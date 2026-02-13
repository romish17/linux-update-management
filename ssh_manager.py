import paramiko
import re
import json
import logging
import requests
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

# Cache for Debian Security Tracker data
_security_tracker_cache = {
    'data': None,
    'timestamp': None,
    'ttl': timedelta(hours=6)  # Cache for 6 hours
}


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


def get_debian_security_tracker_data():
    """
    Fetch CVE data from Debian Security Tracker
    Returns cached data if available and not expired
    """
    global _security_tracker_cache

    now = datetime.now()

    # Check if cache is valid
    if (_security_tracker_cache['data'] is not None and
        _security_tracker_cache['timestamp'] is not None and
        now - _security_tracker_cache['timestamp'] < _security_tracker_cache['ttl']):
        logger.info("Using cached Debian Security Tracker data")
        return _security_tracker_cache['data']

    # Fetch fresh data
    try:
        logger.info("Fetching fresh data from Debian Security Tracker...")
        url = "https://security-tracker.debian.org/tracker/data/json"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            _security_tracker_cache['data'] = data
            _security_tracker_cache['timestamp'] = now
            logger.info(f"Successfully fetched {len(data)} CVE entries from Debian Security Tracker")
            return data
        else:
            logger.error(f"Failed to fetch Debian Security Tracker data: HTTP {response.status_code}")
            return _security_tracker_cache['data']  # Return old cache if available

    except Exception as e:
        logger.error(f"Error fetching Debian Security Tracker data: {str(e)}")
        return _security_tracker_cache['data']  # Return old cache if available


def find_cves_for_packages(packages, debian_version='bookworm'):
    """
    Find CVEs for given packages using Debian Security Tracker

    Args:
        packages: List of package names
        debian_version: Debian release codename (bookworm, bullseye, etc.)

    Returns:
        List of CVE dictionaries with id, package, severity
    """
    security_data = get_debian_security_tracker_data()

    if not security_data:
        logger.warning("No Debian Security Tracker data available")
        return []

    cves = []
    critical_cves = []

    # Map severity from Debian to our scale
    severity_map = {
        'high': 'critical',
        'medium': 'high',
        'low': 'medium',
        'unimportant': 'low'
    }

    for cve_id, cve_data in security_data.items():
        if not cve_id.startswith('CVE-'):
            continue

        # Check if any of our packages are affected
        for release, release_data in cve_data.get('releases', {}).items():
            # Match debian version (bookworm = debian 12, bullseye = debian 11, etc.)
            if debian_version not in release:
                continue

            for package in packages:
                # Get package source name (some binary packages come from different source)
                package_base = package.split(':')[0]  # Remove architecture

                # Check if package is affected
                if package_base in str(release_data):
                    status = release_data.get('status', 'unknown')
                    urgency = release_data.get('urgency', 'medium').lower()

                    # Only include open/unfixed CVEs
                    if status in ['open', 'needed', '']:
                        severity = severity_map.get(urgency, 'medium')

                        # Check if it's critical based on package importance
                        critical_packages = [
                            'linux-image', 'linux-headers', 'kernel',
                            'openssl', 'libssl',
                            'openssh', 'ssh',
                            'sudo', 'systemd',
                            'glibc', 'libc6',
                            'bind9', 'apache2', 'nginx'
                        ]

                        if any(crit_pkg in package_base for crit_pkg in critical_packages):
                            if severity in ['high', 'medium']:
                                severity = 'critical'

                        cve_entry = {
                            'id': cve_id,
                            'package': package,
                            'severity': severity
                        }

                        # Avoid duplicates
                        if not any(c['id'] == cve_id and c['package'] == package for c in cves):
                            cves.append(cve_entry)

                            if severity == 'critical':
                                critical_cves.append(cve_id)

                        break  # Found package, move to next CVE

    return {
        'cves': cves,
        'critical': list(set(critical_cves))  # Remove duplicates
    }


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

            # Only check for CVE if we have security packages OR if total packages < 15
            packages_to_check = []
            if security_packages:
                logger.info(f"Security packages found: {security_packages[:5]}")  # Log first 5
                packages_to_check = security_packages
            elif len(packages) > 0 and len(packages) <= 15:
                # Only check all packages if there aren't too many (to avoid timeout)
                logger.info("No -security packages - checking all packages for CVE (limited)")
                packages_to_check = [p['name'] for p in packages]
            else:
                logger.info(f"Skipping CVE check: {len(packages)} packages but none marked as security")

            if packages_to_check:
                cve_result = DebianUpdateManager.get_cve_info(ssh_manager, packages_to_check)
                cve_info = cve_result.get('cves', [])
                critical_cves = cve_result.get('critical', [])

                if cve_info:
                    # Update security package count based on CVE findings
                    security_packages = list(set([cve['package'] for cve in cve_info]))
                    logger.info(f"CVE detection result: {len(cve_info)} CVEs found, {len(critical_cves)} critical in {len(security_packages)} packages")
                else:
                    logger.info("No CVE found in checked packages")

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
    def detect_debian_version(ssh_manager):
        """Detect Debian version codename"""
        try:
            result = ssh_manager.execute_command('lsb_release -cs 2>/dev/null || cat /etc/debian_version')
            if result['success'] and result['output']:
                version = result['output'].strip().lower()
                # Map version numbers to codenames if needed
                version_map = {
                    '12': 'bookworm',
                    '11': 'bullseye',
                    '10': 'buster'
                }
                return version_map.get(version.split('.')[0], version)
            return 'bookworm'  # Default to latest stable
        except:
            return 'bookworm'

    @staticmethod
    def get_cve_info(ssh_manager, packages):
        """Get CVE information for security packages using Debian Security Tracker"""
        try:
            logger.info(f"Starting CVE detection for {len(packages)} packages")

            # Detect Debian version
            debian_version = DebianUpdateManager.detect_debian_version(ssh_manager)
            logger.info(f"Detected Debian version: {debian_version}")

            # Method 1: Use Debian Security Tracker (most reliable for Debian)
            logger.info("Querying Debian Security Tracker API...")
            tracker_result = find_cves_for_packages(packages, debian_version=debian_version)

            if tracker_result['cves']:
                logger.info(f"Debian Security Tracker found {len(tracker_result['cves'])} CVEs, {len(tracker_result['critical'])} critical")
                return tracker_result

            # Method 2: Fallback to apt-cache show if tracker returns nothing
            logger.info("No CVEs from tracker, falling back to apt-cache show...")
            cves = []
            critical = []

            # Use only apt-cache show (fast) - skip apt-get changelog (too slow)
            for package in packages[:10]:
                changelog_cmd = f"apt-cache show {package} 2>/dev/null | grep -i 'cve-' || true"
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
