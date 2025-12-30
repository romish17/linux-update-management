import paramiko
import re
import json
from config import Config


class SSHManager:
    def __init__(self, hostname, port, username, ssh_key_path=None, password=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.password = password
        self.client = None

    def connect(self):
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.ssh_key_path:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    key_filename=self.ssh_key_path,
                    timeout=Config.SSH_TIMEOUT
                )
            else:
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=Config.SSH_TIMEOUT
                )
            return True
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()

    def execute_command(self, command):
        """Execute a command and return output"""
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')

            return {
                'success': exit_status == 0,
                'output': output,
                'error': error,
                'exit_status': exit_status
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_status': -1
            }

    def detect_os_type(self):
        """Detect if the system is Debian-based or RHEL-based"""
        result = self.execute_command('cat /etc/os-release')
        if result['success']:
            output = result['output'].lower()
            if 'debian' in output or 'ubuntu' in output:
                return 'debian'
            elif 'almalinux' in output or 'rhel' in output or 'centos' in output or 'rocky' in output:
                return 'almalinux'
        return 'unknown'


class DebianUpdateManager:
    """Manage updates for Debian-based systems"""

    @staticmethod
    def check_updates(ssh_manager, security_only=False):
        """Check for available updates"""
        # Update package lists
        ssh_manager.execute_command('sudo apt-get update')

        # Check for upgradable packages
        result = ssh_manager.execute_command('apt list --upgradable 2>/dev/null | grep -v "Listing"')

        if result['success']:
            lines = [line for line in result['output'].split('\n') if line.strip()]

            # Parse package details
            packages = []
            for line in lines:
                # Format: package/version arch version [arch]
                match = re.match(r'(\S+)/\S+\s+(\S+)\s+\S+\s+\[upgradable from:\s+(\S+)\]', line)
                if match:
                    pkg_name = match.group(1)
                    new_version = match.group(2)
                    old_version = match.group(3)

                    # Check if it's a security update
                    is_security = '-security' in line or 'security' in line.lower()

                    packages.append({
                        'name': pkg_name,
                        'old_version': old_version,
                        'new_version': new_version,
                        'is_security': is_security
                    })

            # Filter security updates if requested
            if security_only:
                packages = [p for p in packages if p['is_security']]

            return {
                'success': True,
                'count': len(packages),
                'packages': packages,
                'output': result['output']
            }
        return {
            'success': False,
            'count': 0,
            'packages': [],
            'output': result['error']
        }

    @staticmethod
    def apply_updates(ssh_manager, security_only=False):
        """Apply all available updates or security updates only"""
        if security_only:
            # Install only security updates
            result = ssh_manager.execute_command(
                'sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dir::Etc::SourceList=/etc/apt/sources.list.d/security.list'
            )
            # Alternative method using unattended-upgrades
            if not result['success']:
                result = ssh_manager.execute_command(
                    'sudo DEBIAN_FRONTEND=noninteractive unattended-upgrade -d'
                )
        else:
            # Apply all updates
            result = ssh_manager.execute_command('sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y')

        if result['success']:
            # Parse output to extract package details
            output = result['output']

            # Get count of upgraded packages
            match = re.search(r'(\d+)\s+upgraded', output)
            count = int(match.group(1)) if match else 0

            # Extract package names and versions from output
            packages = []
            for line in output.split('\n'):
                # Match lines like: "Setting up package-name (version) ..."
                match = re.match(r'Setting up (\S+)\s+\(([^)]+)\)', line)
                if match:
                    packages.append({
                        'name': match.group(1),
                        'version': match.group(2)
                    })

            return {
                'success': True,
                'count': count,
                'packages': packages,
                'output': output
            }
        return {
            'success': False,
            'count': 0,
            'packages': [],
            'output': result['error']
        }


class AlmaLinuxUpdateManager:
    """Manage updates for RHEL-based systems (AlmaLinux, CentOS, Rocky)"""

    @staticmethod
    def check_updates(ssh_manager, security_only=False):
        """Check for available updates"""
        # Try dnf first, fall back to yum
        result = ssh_manager.execute_command('which dnf')
        pkg_manager = 'dnf' if result['success'] else 'yum'

        if security_only:
            # Check for security updates only
            result = ssh_manager.execute_command(f'{pkg_manager} updateinfo list security --available')
        else:
            result = ssh_manager.execute_command(f'{pkg_manager} check-update -q')

        # check-update returns exit code 100 if updates are available
        if result['exit_status'] in [0, 100] or result['success']:
            lines = [line for line in result['output'].split('\n') if line.strip()]

            # Parse package details
            packages = []
            for line in lines:
                if not line.strip() or line.startswith('Last metadata') or line.startswith('Security:'):
                    continue

                # Format: package.arch version repo
                parts = line.split()
                if len(parts) >= 3 and '.' in parts[0]:
                    pkg_name = parts[0]
                    new_version = parts[1]
                    repo = parts[2] if len(parts) > 2 else 'unknown'

                    is_security = 'security' in repo.lower() or security_only

                    packages.append({
                        'name': pkg_name,
                        'new_version': new_version,
                        'repo': repo,
                        'is_security': is_security
                    })

            return {
                'success': True,
                'count': len(packages),
                'packages': packages,
                'output': result['output']
            }
        return {
            'success': False,
            'count': 0,
            'packages': [],
            'output': result['error']
        }

    @staticmethod
    def apply_updates(ssh_manager, security_only=False):
        """Apply all available updates or security updates only"""
        result = ssh_manager.execute_command('which dnf')
        pkg_manager = 'dnf' if result['success'] else 'yum'

        if security_only:
            # Apply security updates only
            result = ssh_manager.execute_command(f'sudo {pkg_manager} update --security -y')
        else:
            # Apply all updates
            result = ssh_manager.execute_command(f'sudo {pkg_manager} update -y')

        if result['success'] or result['exit_status'] == 0:
            # Parse output to extract package details
            output = result['output']

            # Extract installed/upgraded packages
            packages = []
            in_transaction = False
            for line in output.split('\n'):
                if 'Installing:' in line or 'Upgrading:' in line:
                    in_transaction = True
                    continue
                if in_transaction and line.strip():
                    # Format: " package-name arch version repo size"
                    parts = line.split()
                    if len(parts) >= 3:
                        packages.append({
                            'name': parts[0],
                            'version': parts[2] if len(parts) > 2 else parts[1]
                        })
                if 'Complete!' in line:
                    break

            return {
                'success': True,
                'count': len(packages),
                'packages': packages,
                'output': output
            }
        return {
            'success': False,
            'count': 0,
            'packages': [],
            'output': result['error']
        }


def get_update_manager(os_type):
    """Return the appropriate update manager for the OS type"""
    if os_type == 'debian':
        return DebianUpdateManager()
    elif os_type == 'almalinux':
        return AlmaLinuxUpdateManager()
    else:
        raise ValueError(f"Unsupported OS type: {os_type}")
