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
        try:
            # Update package lists
            update_result = ssh_manager.execute_command('sudo apt-get update')
            if not update_result['success']:
                error_msg = f"Failed to update package lists: {update_result['error']}\nOutput: {update_result['output']}"
                return {
                    'success': False,
                    'count': 0,
                    'packages': [],
                    'output': error_msg
                }

            # Check for upgradable packages
            # Note: grep returns exit code 1 when no matches found, which is normal
            result = ssh_manager.execute_command('apt list --upgradable 2>/dev/null | grep -v "Listing"')

            # Exit codes 0 (found results) and 1 (no results from grep) are both valid
            if result['exit_status'] not in [0, 1]:
                error_msg = f"Failed to list upgradable packages: {result['error']}\nOutput: {result['output']}\nExit code: {result['exit_status']}"
                return {
                    'success': False,
                    'count': 0,
                    'packages': [],
                    'output': error_msg
                }

            lines = [line for line in result['output'].split('\n') if line.strip()]

            # Parse package details
            packages = []
            security_packages = []
            for line in lines:
                # Format: package/version arch version [arch]
                match = re.match(r'(\S+)/\S+\s+(\S+)\s+\S+\s+\[upgradable from:\s+(\S+)\]', line)
                if match:
                    pkg_name = match.group(1)
                    new_version = match.group(2)
                    old_version = match.group(3)

                    # Check if it's a security update
                    is_security = '-security' in line or 'security' in line.lower()

                    package_info = {
                        'name': pkg_name,
                        'old_version': old_version,
                        'new_version': new_version,
                        'is_security': is_security
                    }

                    packages.append(package_info)
                    if is_security:
                        security_packages.append(pkg_name)

            # Get CVE information for security updates
            cve_info = []
            critical_cves = []

            # Debug logging
            logger.info(f"Total packages: {len(packages)}, Security packages: {len(security_packages)}")

            if security_packages:
                logger.info(f"Security packages found: {security_packages[:5]}")  # Log first 5
                cve_result = DebianUpdateManager.get_cve_info(ssh_manager, security_packages)
                cve_info = cve_result.get('cves', [])
                critical_cves = cve_result.get('critical', [])
                logger.info(f"CVE detection result: {len(cve_info)} CVEs found, {len(critical_cves)} critical")
            else:
                # No security packages detected via -security repo
                # But we still check all packages for CVE (limited to first 10)
                logger.warning("No -security packages detected - checking all packages for CVE")
                all_package_names = [p['name'] for p in packages]
                if all_package_names:
                    cve_result = DebianUpdateManager.get_cve_info(ssh_manager, all_package_names)
                    cve_info = cve_result.get('cves', [])
                    critical_cves = cve_result.get('critical', [])
                    # Update security package count based on CVE findings
                    if cve_info:
                        security_packages = list(set([cve['package'] for cve in cve_info]))
                        logger.info(f"CVE found in {len(security_packages)} packages: {len(cve_info)} CVEs, {len(critical_cves)} critical")

            # Filter security updates if requested
            if security_only:
                packages = [p for p in packages if p['is_security']]

            # Generate appropriate message
            if len(packages) == 0:
                output_msg = "System is up to date - no updates available"
            else:
                output_msg = f"Found {len(packages)} updates available"
                if len(security_packages) > 0:
                    output_msg += f"\n⚠️  {len(security_packages)} security updates"
                if len(critical_cves) > 0:
                    output_msg += f"\n🔴 {len(critical_cves)} CRITICAL vulnerabilities"
                    output_msg += f"\n   CVEs: {', '.join(critical_cves)}"
                if len(lines) > 0:
                    output_msg += f"\n\nUpgradable packages:\n{result['output']}"

            return {
                'success': True,
                'count': len(packages),
                'packages': packages,
                'output': output_msg,
                'security_count': len(security_packages),
                'cve_info': cve_info,
                'critical_cves': critical_cves
            }
        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'packages': [],
                'output': f"Exception in check_updates: {str(e)}",
                'security_count': 0,
                'cve_info': [],
                'critical_cves': []
            }

    @staticmethod
    def get_cve_info(ssh_manager, packages):
        """Get CVE information for security packages"""
        try:
            cves = []
            critical = []

            logger.info(f"Starting CVE detection for {len(packages)} packages (checking first 10)")

            # Try to get CVE info from apt changelog (limit to first 10 to avoid slowdown)
            for package in packages[:10]:
                # Method 1: apt-cache show (fast but may not have CVE info)
                changelog_cmd = f"apt-cache show {package} 2>/dev/null | grep -i 'cve-' || true"
                result = ssh_manager.execute_command(changelog_cmd)

                # Method 2: If no CVE found, try apt-get changelog (slower but more complete)
                if not result['output']:
                    changelog_cmd = f"apt-get changelog {package} 2>/dev/null | head -50 | grep -i 'cve-' || true"
                    result = ssh_manager.execute_command(changelog_cmd)

                logger.debug(f"CVE check for {package}: output={'found' if result['output'] else 'none'}")

                if result['output']:
                    # Extract CVE IDs
                    cve_matches = re.findall(r'CVE-\d{4}-\d+', result['output'], re.IGNORECASE)
                    for cve in cve_matches:
                        cve_upper = cve.upper()
                        if cve_upper not in [c['id'] for c in cves]:
                            # Determine severity based on package type
                            severity = 'medium'
                            pkg_name = package.lower()

                            # Critical packages that should be prioritized
                            critical_packages = [
                                'linux-image', 'linux-headers', 'kernel',
                                'openssl', 'libssl',
                                'openssh', 'ssh',
                                'sudo',
                                'systemd',
                                'glibc', 'libc6',
                                'bind9', 'apache2', 'nginx'
                            ]

                            if any(crit_pkg in pkg_name for crit_pkg in critical_packages):
                                severity = 'critical'
                                critical.append(cve_upper)
                            elif 'security' in pkg_name:
                                severity = 'high'

                            cve_entry = {
                                'id': cve_upper,
                                'package': package,
                                'severity': severity
                            }
                            cves.append(cve_entry)

            return {
                'cves': cves,
                'critical': critical
            }

        except Exception as e:
            return {
                'cves': [],
                'critical': []
            }

    @staticmethod
    def apply_updates(ssh_manager, security_only=False):
        """Apply all available updates or security updates only"""
        # Dpkg options to avoid configuration file prompts
        # --force-confold: keep existing config files
        # --force-confdef: use default option (usually keep existing)
        dpkg_opts = '-o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-confdef"'

        if security_only:
            # Install only security updates
            result = ssh_manager.execute_command(
                f'sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y {dpkg_opts} -o Dir::Etc::SourceList=/etc/apt/sources.list.d/security.list'
            )
            # Alternative method using unattended-upgrades
            if not result['success']:
                result = ssh_manager.execute_command(
                    'sudo DEBIAN_FRONTEND=noninteractive unattended-upgrade -d'
                )
        else:
            # Apply all updates
            result = ssh_manager.execute_command(
                f'sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y {dpkg_opts}'
            )

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
        try:
            # Try dnf first, fall back to yum
            result = ssh_manager.execute_command('which dnf')
            pkg_manager = 'dnf' if result['success'] else 'yum'

            if security_only:
                # Check for security updates only
                result = ssh_manager.execute_command(f'{pkg_manager} updateinfo list security --available')
            else:
                result = ssh_manager.execute_command(f'{pkg_manager} check-update -q')

            # check-update returns exit code 100 if updates are available, 0 if no updates
            if result['exit_status'] in [0, 100] or result['success']:
                lines = [line for line in result['output'].split('\n') if line.strip()]

                # Parse package details
                packages = []
                security_packages = []
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

                        if is_security:
                            security_packages.append(pkg_name)

                # Get CVE information for security updates
                cve_info = []
                critical_cves = []
                if security_packages:
                    cve_result = AlmaLinuxUpdateManager.get_cve_info(ssh_manager, security_packages, pkg_manager)
                    cve_info = cve_result.get('cves', [])
                    critical_cves = cve_result.get('critical', [])

                # Generate appropriate message
                if len(packages) == 0:
                    output_msg = "System is up to date - no updates available"
                else:
                    output_msg = f"Found {len(packages)} updates available using {pkg_manager}"
                    if len(security_packages) > 0:
                        output_msg += f"\n⚠️  {len(security_packages)} security updates"
                    if len(critical_cves) > 0:
                        output_msg += f"\n🔴 {len(critical_cves)} CRITICAL vulnerabilities"
                        output_msg += f"\n   CVEs: {', '.join(critical_cves)}"
                    if len(lines) > 0:
                        output_msg += f"\n\nAvailable updates:\n{result['output']}"

                return {
                    'success': True,
                    'count': len(packages),
                    'packages': packages,
                    'output': output_msg,
                    'security_count': len(security_packages),
                    'cve_info': cve_info,
                    'critical_cves': critical_cves
                }

            error_msg = f"Failed to check updates using {pkg_manager}"
            if result['error']:
                error_msg += f"\nError: {result['error']}"
            if result['output']:
                error_msg += f"\nOutput: {result['output']}"
            error_msg += f"\nExit status: {result['exit_status']}"

            return {
                'success': False,
                'count': 0,
                'packages': [],
                'output': error_msg,
                'security_count': 0,
                'cve_info': [],
                'critical_cves': []
            }
        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'packages': [],
                'output': f"Exception in check_updates: {str(e)}",
                'security_count': 0,
                'cve_info': [],
                'critical_cves': []
            }

    @staticmethod
    def get_cve_info(ssh_manager, packages, pkg_manager):
        """Get CVE information for security packages using dnf/yum updateinfo"""
        try:
            cves = []
            critical = []

            # Get CVE info using updateinfo (limit to first 10 to avoid slowdown)
            for package in packages[:10]:
                # Get detailed security info for the package
                info_cmd = f"{pkg_manager} updateinfo info {package} 2>/dev/null || true"
                result = ssh_manager.execute_command(info_cmd)

                if result['output']:
                    # Extract CVE IDs from updateinfo output
                    cve_matches = re.findall(r'CVE-\d{4}-\d+', result['output'], re.IGNORECASE)

                    for cve in cve_matches:
                        cve_upper = cve.upper()
                        if cve_upper not in [c['id'] for c in cves]:
                            # Determine severity based on package type
                            severity = 'medium'
                            pkg_name = package.lower()

                            # Check severity from updateinfo output
                            if 'Severity : Critical' in result['output'] or 'Type : Security' in result['output']:
                                severity_match = re.search(r'Severity\s*:\s*(\w+)', result['output'], re.IGNORECASE)
                                if severity_match:
                                    sev_level = severity_match.group(1).lower()
                                    if sev_level in ['critical', 'important']:
                                        severity = 'critical'
                                    elif sev_level in ['high', 'moderate']:
                                        severity = 'high'

                            # Critical packages that should be prioritized
                            critical_packages = [
                                'kernel', 'linux',
                                'openssl',
                                'openssh', 'ssh',
                                'sudo',
                                'systemd',
                                'glibc',
                                'bind', 'httpd', 'nginx'
                            ]

                            if any(crit_pkg in pkg_name for crit_pkg in critical_packages):
                                severity = 'critical'

                            if severity == 'critical':
                                critical.append(cve_upper)

                            cve_entry = {
                                'id': cve_upper,
                                'package': package,
                                'severity': severity
                            }
                            cves.append(cve_entry)

            return {
                'cves': cves,
                'critical': critical
            }

        except Exception as e:
            return {
                'cves': [],
                'critical': []
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


def check_reboot_required(ssh_manager, os_type):
    """Check if a reboot is required after updates"""
    if os_type == 'debian':
        # Debian/Ubuntu creates this file when reboot is needed
        result = ssh_manager.execute_command('[ -f /var/run/reboot-required ] && echo "reboot_required" || echo "no_reboot"')
        return 'reboot_required' in result['output']
    else:  # almalinux
        # Use needs-restarting command
        result = ssh_manager.execute_command('needs-restarting -r')
        # Exit code 1 means reboot required
        return result['exit_status'] == 1


def reboot_server(ssh_manager, delay_minutes=1):
    """
    Reboot the server with a delay

    Args:
        ssh_manager: SSHManager instance
        delay_minutes: Delay in minutes before reboot (default: 1)

    Returns:
        dict with success status and message
    """
    result = ssh_manager.execute_command(f'sudo shutdown -r +{delay_minutes} "Server rebooting for updates"')

    return {
        'success': result['success'],
        'message': f'Server will reboot in {delay_minutes} minute(s)',
        'output': result['output']
    }
