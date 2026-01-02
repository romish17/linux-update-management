"""
Server Provisioning Module
Automated SSH setup and user creation on remote servers
"""

import os
import logging
from pathlib import Path
from ssh_manager import SSHManager

logger = logging.getLogger(__name__)

# Configuration
LUM_USER = 'lum-user'
SSH_KEY_DIR = '/app/data/ssh_keys'
SSH_KEY_NAME = 'lum_rsa'


class ServerProvisioner:
    """Handle automated provisioning of remote servers"""

    def __init__(self):
        self.ssh_key_dir = Path(SSH_KEY_DIR)
        self.ssh_key_dir.mkdir(parents=True, exist_ok=True)
        self.private_key_path = self.ssh_key_dir / SSH_KEY_NAME
        self.public_key_path = self.ssh_key_dir / f'{SSH_KEY_NAME}.pub'

    def ensure_ssh_key(self):
        """Generate SSH key pair if it doesn't exist"""
        if not self.private_key_path.exists():
            logger.info("Generating new SSH key pair...")
            import subprocess

            result = subprocess.run([
                'ssh-keygen',
                '-t', 'rsa',
                '-b', '4096',
                '-f', str(self.private_key_path),
                '-N', '',  # No passphrase
                '-C', 'linux-update-manager'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"Failed to generate SSH key: {result.stderr}")

            # Set correct permissions
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)

            logger.info("SSH key pair generated successfully")

        return str(self.private_key_path), str(self.public_key_path)

    def get_public_key(self):
        """Read and return the public key"""
        if not self.public_key_path.exists():
            self.ensure_ssh_key()

        with open(self.public_key_path, 'r') as f:
            return f.read().strip()

    def get_sudoers_config(self, os_type):
        """Get sudoers configuration for the LUM user based on OS type"""
        if os_type == 'debian':
            commands = [
                '/usr/bin/apt-get',
                '/usr/bin/apt',
                '/usr/bin/dpkg',
                '/usr/bin/apt-cache',
                '/sbin/reboot',
                '/sbin/shutdown'
            ]
        else:  # almalinux/rhel
            commands = [
                '/usr/bin/yum',
                '/usr/bin/dnf',
                '/usr/bin/rpm',
                '/sbin/reboot',
                '/sbin/shutdown'
            ]

        # Create sudoers rule
        commands_str = ', '.join(commands)
        sudoers_line = f"{LUM_USER} ALL=(ALL) NOPASSWD: {commands_str}"

        return sudoers_line

    def provision_server(self, hostname, port, root_username, root_password, os_type):
        """
        Provision a server with automated SSH setup

        Steps:
        1. Connect with root credentials
        2. Generate/get SSH key
        3. Create lum-user
        4. Setup SSH key authentication
        5. Configure sudoers
        6. Test connection with new user

        Returns:
            dict: Provisioning result with status and details
        """
        result = {
            'success': False,
            'steps': [],
            'username': LUM_USER,
            'ssh_key_path': str(self.private_key_path)
        }

        try:
            # Step 1: Ensure SSH key exists
            result['steps'].append({'name': 'generate_ssh_key', 'status': 'running'})
            private_key, public_key = self.ensure_ssh_key()
            pub_key_content = self.get_public_key()
            result['steps'][-1]['status'] = 'success'
            result['steps'][-1]['message'] = 'SSH key ready'

            # Step 2: Connect with root credentials
            result['steps'].append({'name': 'connect_root', 'status': 'running'})
            ssh = SSHManager(
                hostname=hostname,
                port=port,
                username=root_username,
                password=root_password
            )

            connect_result = ssh.connect()
            if connect_result is not True:
                raise Exception(f"Failed to connect: {connect_result[1]}")

            result['steps'][-1]['status'] = 'success'
            result['steps'][-1]['message'] = f'Connected as {root_username}'

            # Step 3: Create lum-user
            result['steps'].append({'name': 'create_user', 'status': 'running'})

            # Check if user already exists
            check_user = f"id {LUM_USER} >/dev/null 2>&1 && echo 'exists' || echo 'not_exists'"
            check_result = ssh.execute_command(check_user)
            user_exists = check_result['output'].strip()

            if user_exists == 'not_exists':
                # Create user with home directory
                create_cmd = f"useradd -m -s /bin/bash {LUM_USER}"
                create_result = ssh.execute_command(create_cmd)

                if create_result['exit_status'] != 0:
                    raise Exception(f"Failed to create user: {create_result['error']}")

                result['steps'][-1]['message'] = f'User {LUM_USER} created'
            else:
                result['steps'][-1]['message'] = f'User {LUM_USER} already exists'

            result['steps'][-1]['status'] = 'success'

            # Step 4: Setup SSH directory and authorized_keys
            result['steps'].append({'name': 'setup_ssh', 'status': 'running'})

            ssh_setup_commands = [
                f"mkdir -p /home/{LUM_USER}/.ssh",
                f"chmod 700 /home/{LUM_USER}/.ssh",
                f"echo '{pub_key_content}' > /home/{LUM_USER}/.ssh/authorized_keys",
                f"chmod 600 /home/{LUM_USER}/.ssh/authorized_keys",
                f"chown -R {LUM_USER}:{LUM_USER} /home/{LUM_USER}/.ssh"
            ]

            for cmd in ssh_setup_commands:
                cmd_result = ssh.execute_command(cmd)
                if cmd_result['exit_status'] != 0:
                    raise Exception(f"SSH setup failed: {cmd_result['error']}")

            result['steps'][-1]['status'] = 'success'
            result['steps'][-1]['message'] = 'SSH key deployed'

            # Step 5: Ensure sudo is installed
            result['steps'].append({'name': 'install_sudo', 'status': 'running'})

            # Check if sudo is installed
            check_sudo = ssh.execute_command('which sudo')
            if check_sudo['exit_status'] != 0:
                logger.info(f"sudo not found on {hostname}, installing...")

                # Install sudo based on OS type
                if os_type == 'debian':
                    install_cmd = 'apt-get update && apt-get install -y sudo'
                else:  # almalinux/rhel
                    install_cmd = 'yum install -y sudo || dnf install -y sudo'

                install_result = ssh.execute_command(install_cmd)
                if install_result['exit_status'] != 0:
                    raise Exception(f"Failed to install sudo: {install_result['error']}")

                result['steps'][-1]['message'] = 'sudo installed'
            else:
                result['steps'][-1]['message'] = 'sudo already installed'

            result['steps'][-1]['status'] = 'success'

            # Step 6: Configure sudoers
            result['steps'].append({'name': 'configure_sudoers', 'status': 'running'})

            sudoers_config = self.get_sudoers_config(os_type)
            sudoers_file = f"/etc/sudoers.d/{LUM_USER}"

            # Ensure sudoers.d directory exists
            mkdir_result = ssh.execute_command("mkdir -p /etc/sudoers.d")
            if mkdir_result['exit_status'] != 0:
                raise Exception(f"Failed to create sudoers.d directory: {mkdir_result['error']}")

            # Ensure /etc/sudoers includes sudoers.d directory
            check_include = ssh.execute_command("grep -q '#includedir /etc/sudoers.d' /etc/sudoers || grep -q '@includedir /etc/sudoers.d' /etc/sudoers")
            if check_include['exit_status'] != 0:
                # Add includedir directive to /etc/sudoers
                add_include = ssh.execute_command("echo '@includedir /etc/sudoers.d' >> /etc/sudoers")
                if add_include['exit_status'] != 0:
                    logger.warning(f"Could not add includedir to /etc/sudoers: {add_include['error']}")

            sudoers_commands = [
                f"echo '{sudoers_config}' > {sudoers_file}",
                f"chmod 440 {sudoers_file}",
                f"visudo -c -f {sudoers_file}"  # Validate sudoers syntax
            ]

            for cmd in sudoers_commands:
                cmd_result = ssh.execute_command(cmd)
                if cmd_result['exit_status'] != 0:
                    raise Exception(f"Sudoers configuration failed: {cmd_result['error']}")

            result['steps'][-1]['status'] = 'success'
            result['steps'][-1]['message'] = 'Sudo permissions configured'

            # Disconnect root session
            ssh.disconnect()

            # Step 7: Test connection with new user
            result['steps'].append({'name': 'test_connection', 'status': 'running'})

            test_ssh = SSHManager(
                hostname=hostname,
                port=port,
                username=LUM_USER,
                ssh_key_path=str(self.private_key_path)
            )

            test_connect = test_ssh.connect()
            if test_connect is not True:
                raise Exception(f"Test connection failed: {test_connect[1]}")

            # Test sudo permissions
            if os_type == 'debian':
                test_cmd = 'sudo apt-get --version'
            else:
                test_cmd = 'sudo yum --version'

            test_result = test_ssh.execute_command(test_cmd)
            if test_result['exit_status'] != 0:
                raise Exception(f"Sudo test failed: {test_result['error']}")

            test_ssh.disconnect()

            result['steps'][-1]['status'] = 'success'
            result['steps'][-1]['message'] = 'Connection and sudo verified'

            # All steps successful
            result['success'] = True
            result['message'] = 'Server provisioned successfully'

        except Exception as e:
            logger.error(f"Provisioning failed: {str(e)}")

            # Mark last step as failed
            if result['steps']:
                result['steps'][-1]['status'] = 'failed'
                result['steps'][-1]['error'] = str(e)

            result['success'] = False
            result['error'] = str(e)

        return result

    def regenerate_ssh_key(self):
        """Regenerate SSH key pair"""
        # Remove existing keys
        if self.private_key_path.exists():
            self.private_key_path.unlink()
        if self.public_key_path.exists():
            self.public_key_path.unlink()

        # Generate new keys
        return self.ensure_ssh_key()

    def get_ssh_key_info(self):
        """Get information about the SSH key"""
        if not self.private_key_path.exists():
            return {
                'exists': False,
                'message': 'No SSH key generated yet'
            }

        # Get key fingerprint
        import subprocess
        result = subprocess.run([
            'ssh-keygen',
            '-lf',
            str(self.public_key_path)
        ], capture_output=True, text=True)

        fingerprint = result.stdout.strip() if result.returncode == 0 else 'Unknown'

        # Get file stats
        stat_info = self.private_key_path.stat()

        return {
            'exists': True,
            'private_key_path': str(self.private_key_path),
            'public_key_path': str(self.public_key_path),
            'fingerprint': fingerprint,
            'created': stat_info.st_mtime,
            'public_key': self.get_public_key()
        }
