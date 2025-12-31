"""
Auto-update manager for configuring automatic updates on remote servers
"""
import json
from ssh_manager import SSHManager


class AutoUpdateConfigurator:
    """Configure automatic updates on remote servers"""

    @staticmethod
    def configure_debian_auto_updates(ssh_manager, schedule, update_type='all', auto_reboot=False):
        """
        Configure unattended-upgrades on Debian/Ubuntu

        Args:
            ssh_manager: SSHManager instance
            schedule: ScheduledUpdate model instance
            update_type: 'all' or 'security'
            auto_reboot: bool, whether to auto-reboot if needed
        """
        cron_expr = schedule.get_cron_expression()
        if not cron_expr:
            return {'success': False, 'error': 'Invalid schedule'}

        # Install unattended-upgrades if not present
        install_result = ssh_manager.execute_command(
            'sudo apt-get install -y unattended-upgrades apt-listchanges'
        )

        # Create configuration file
        config_content = f'''// Automatically upgrade packages from these origins
Unattended-Upgrade::Allowed-Origins {{
    "${{distro_id}}:${{distro_codename}}-security";
'''

        if update_type == 'all':
            config_content += '''    "${distro_id}:${distro_codename}-updates";
    "${distro_id}:${distro_codename}";
'''

        config_content += f'''}};

// Automatically reboot *WITHOUT CONFIRMATION* if needed
Unattended-Upgrade::Automatic-Reboot "{str(auto_reboot).lower()}";

// Reboot time
Unattended-Upgrade::Automatic-Reboot-Time "{schedule.hour:02d}:{schedule.minute:02d}";

// Keep old configuration files (don't prompt)
Dpkg::Options {{
   "--force-confdef";
   "--force-confold";
}};

// Mail configuration (optional)
// Unattended-Upgrade::Mail "root";
// Unattended-Upgrade::MailOnlyOnError "true";

// Remove unused automatically installed kernel-related packages
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";

// Remove unused dependencies
Unattended-Upgrade::Remove-Unused-Dependencies "true";

// Enable logging
Unattended-Upgrade::SyslogEnable "true";
'''

        # Write configuration to remote server
        write_config = ssh_manager.execute_command(
            f"sudo tee /etc/apt/apt.conf.d/50unattended-upgrades > /dev/null << 'EOFCONFIG'\n{config_content}\nEOFCONFIG"
        )

        # Enable automatic updates
        auto_upgrades_config = '''APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
'''

        enable_auto = ssh_manager.execute_command(
            f"sudo tee /etc/apt/apt.conf.d/20auto-upgrades > /dev/null << 'EOFAUTO'\n{auto_upgrades_config}\nEOFAUTO"
        )

        # Configure cron job for scheduled execution
        cron_command = f'unattended-upgrade -v'
        cron_entry = f'{cron_expr} root {cron_command} >> /var/log/unattended-upgrades/cron.log 2>&1'

        add_cron = ssh_manager.execute_command(
            f"echo '{cron_entry}' | sudo tee /etc/cron.d/linux-update-manager > /dev/null"
        )

        return {
            'success': all([install_result['success'], write_config['success'],
                          enable_auto['success'], add_cron['success']]),
            'output': f"Configuration installée avec succès.\nCron: {cron_expr}",
            'cron_expression': cron_expr
        }

    @staticmethod
    def configure_almalinux_auto_updates(ssh_manager, schedule, update_type='all', auto_reboot=False):
        """
        Configure dnf-automatic on AlmaLinux/RHEL

        Args:
            ssh_manager: SSHManager instance
            schedule: ScheduledUpdate model instance
            update_type: 'all' or 'security'
            auto_reboot: bool, whether to auto-reboot if needed
        """
        cron_expr = schedule.get_cron_expression()
        if not cron_expr:
            return {'success': False, 'error': 'Invalid schedule'}

        # Detect package manager
        detect_dnf = ssh_manager.execute_command('which dnf')
        pkg_manager = 'dnf' if detect_dnf['success'] else 'yum'

        # Install dnf-automatic or yum-cron
        if pkg_manager == 'dnf':
            install_result = ssh_manager.execute_command('sudo dnf install -y dnf-automatic')
            config_file = '/etc/dnf/automatic.conf'
            service_name = 'dnf-automatic.timer'
        else:
            install_result = ssh_manager.execute_command('sudo yum install -y yum-cron')
            config_file = '/etc/yum/yum-cron.conf'
            service_name = 'yum-cron'

        # Create configuration
        upgrade_cmd = 'security' if update_type == 'security' else 'default'

        if pkg_manager == 'dnf':
            config_content = f'''[commands]
upgrade_type = {upgrade_cmd}
random_sleep = 0
download_updates = yes
apply_updates = yes

[emitters]
emit_via = stdio
system_name = None

[email]
email_from = root@localhost
email_to = root
email_host = localhost

[base]
debuglevel = 1
'''
        else:
            config_content = f'''[commands]
update_cmd = {upgrade_cmd}
download_updates = yes
apply_updates = yes
random_sleep = 0

[emitters]
system_name = None
emit_via = stdio

[email]
email_from = root@localhost
email_to = root
email_host = localhost
'''

        # Write configuration
        write_config = ssh_manager.execute_command(
            f"sudo tee {config_file} > /dev/null << 'EOFCONF'\n{config_content}\nEOFCONF"
        )

        # Disable systemd timer (we'll use cron for scheduling)
        if pkg_manager == 'dnf':
            ssh_manager.execute_command(f'sudo systemctl disable {service_name}')
            ssh_manager.execute_command(f'sudo systemctl stop {service_name}')

        # Configure cron job
        cron_command = f'{pkg_manager}-automatic' if pkg_manager == 'dnf' else 'yum-cron'
        cron_entry = f'{cron_expr} root {cron_command} >> /var/log/{cron_command}.log 2>&1'

        add_cron = ssh_manager.execute_command(
            f"echo '{cron_entry}' | sudo tee /etc/cron.d/linux-update-manager > /dev/null"
        )

        # Configure auto-reboot if needed
        if auto_reboot:
            reboot_script = f'''#!/bin/bash
# Check if reboot is required
if [ -f /var/run/reboot-required ]; then
    /sbin/shutdown -r +5 "System will reboot in 5 minutes for updates"
fi
'''
            ssh_manager.execute_command(
                f"sudo tee /etc/cron.daily/auto-reboot-if-needed > /dev/null << 'EOFREBOOT'\n{reboot_script}\nEOFREBOOT"
            )
            ssh_manager.execute_command('sudo chmod +x /etc/cron.daily/auto-reboot-if-needed')

        return {
            'success': all([install_result['success'], write_config['success'], add_cron['success']]),
            'output': f"Configuration installée avec succès.\nCron: {cron_expr}",
            'cron_expression': cron_expr
        }

    @staticmethod
    def remove_auto_updates(ssh_manager, os_type):
        """Remove automatic update configuration"""
        if os_type == 'debian':
            # Remove cron job
            ssh_manager.execute_command('sudo rm -f /etc/cron.d/linux-update-manager')
            # Optionally disable unattended-upgrades
            ssh_manager.execute_command('sudo systemctl disable unattended-upgrades')
        else:  # almalinux
            # Remove cron job
            ssh_manager.execute_command('sudo rm -f /etc/cron.d/linux-update-manager')
            # Disable services
            ssh_manager.execute_command('sudo systemctl disable dnf-automatic.timer')
            ssh_manager.execute_command('sudo systemctl stop dnf-automatic.timer')
            ssh_manager.execute_command('sudo systemctl disable yum-cron')
            ssh_manager.execute_command('sudo systemctl stop yum-cron')

        return {'success': True, 'output': 'Configuration automatique supprimée'}

    @staticmethod
    def get_auto_update_status(ssh_manager, os_type):
        """Check if automatic updates are configured"""
        # Check for our cron job
        cron_check = ssh_manager.execute_command('sudo cat /etc/cron.d/linux-update-manager 2>/dev/null')

        status = {
            'configured': cron_check['success'] and len(cron_check['output']) > 0,
            'cron_content': cron_check['output'] if cron_check['success'] else None
        }

        if os_type == 'debian':
            # Check unattended-upgrades status
            service_status = ssh_manager.execute_command('systemctl is-enabled unattended-upgrades 2>/dev/null')
            status['service_enabled'] = 'enabled' in service_status['output']
        else:
            # Check dnf-automatic or yum-cron status
            dnf_status = ssh_manager.execute_command('systemctl is-active dnf-automatic.timer 2>/dev/null')
            yum_status = ssh_manager.execute_command('systemctl is-active yum-cron 2>/dev/null')
            status['service_enabled'] = 'active' in dnf_status['output'] or 'active' in yum_status['output']

        return status
