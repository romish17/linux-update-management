import paramiko
import re
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
    def check_updates(ssh_manager):
        """Check for available updates"""
        # Update package lists
        ssh_manager.execute_command('sudo apt-get update')

        # Check for upgradable packages
        result = ssh_manager.execute_command('apt list --upgradable 2>/dev/null | grep -v "Listing"')

        if result['success']:
            lines = [line for line in result['output'].split('\n') if line.strip()]
            count = len(lines)
            return {
                'success': True,
                'count': count,
                'output': result['output']
            }
        return {
            'success': False,
            'count': 0,
            'output': result['error']
        }

    @staticmethod
    def apply_updates(ssh_manager):
        """Apply all available updates"""
        result = ssh_manager.execute_command('sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y')

        if result['success']:
            # Parse output to count updated packages
            output = result['output']
            match = re.search(r'(\d+)\s+upgraded', output)
            count = int(match.group(1)) if match else 0

            return {
                'success': True,
                'count': count,
                'output': output
            }
        return {
            'success': False,
            'count': 0,
            'output': result['error']
        }


class AlmaLinuxUpdateManager:
    """Manage updates for RHEL-based systems (AlmaLinux, CentOS, Rocky)"""

    @staticmethod
    def check_updates(ssh_manager):
        """Check for available updates"""
        # Try dnf first, fall back to yum
        result = ssh_manager.execute_command('which dnf')
        pkg_manager = 'dnf' if result['success'] else 'yum'

        result = ssh_manager.execute_command(f'{pkg_manager} check-update -q')

        # check-update returns exit code 100 if updates are available
        if result['exit_status'] in [0, 100]:
            lines = [line for line in result['output'].split('\n') if line.strip() and not line.startswith('Last metadata')]
            count = len([l for l in lines if '.' in l])  # Filter actual package lines

            return {
                'success': True,
                'count': count,
                'output': result['output']
            }
        return {
            'success': False,
            'count': 0,
            'output': result['error']
        }

    @staticmethod
    def apply_updates(ssh_manager):
        """Apply all available updates"""
        result = ssh_manager.execute_command('which dnf')
        pkg_manager = 'dnf' if result['success'] else 'yum'

        result = ssh_manager.execute_command(f'sudo {pkg_manager} update -y')

        if result['success'] or result['exit_status'] == 0:
            # Parse output to count updated packages
            output = result['output']
            match = re.search(r'Complete!', output)

            # Count "Upgraded:" or "Installed:" lines
            upgraded = len(re.findall(r'^\s+\S+\s+\S+\s+\S+', output, re.MULTILINE))

            return {
                'success': True,
                'count': upgraded,
                'output': output
            }
        return {
            'success': False,
            'count': 0,
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
