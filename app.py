from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from datetime import datetime
from config import Config
from models import db, Server, UpdateHistory, ScheduledUpdate, User
from ssh_manager import SSHManager, get_update_manager, check_reboot_required, reboot_server
from auto_update_manager import AutoUpdateConfigurator
from server_provisioning import ServerProvisioner
from scheduler import update_scheduler
import os
import json
import time
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend development
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://frontend:3000'])

db.init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize scheduler
update_scheduler.init_app(app, db)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    """Return JSON error for unauthorized requests"""
    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401


# Create tables
with app.app_context():
    db.create_all()


@app.route('/api/login', methods=['POST'])
def login():
    """API Login endpoint"""
    if current_user.is_authenticated:
        return jsonify({'success': True, 'message': 'Already authenticated'}), 200

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Nom d\'utilisateur et mot de passe requis'}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.is_active and user.check_password(password):
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        login_user(user, remember=True)

        return jsonify({
            'success': True,
            'message': 'Connexion réussie',
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin
            }
        })
    else:
        return jsonify({'error': 'Nom d\'utilisateur ou mot de passe incorrect'}), 401


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    """API Logout endpoint"""
    logout_user()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})


@app.route('/api/servers', methods=['GET'])
@login_required
def get_servers():
    """Get all servers"""
    servers = Server.query.all()
    return jsonify([server.to_dict() for server in servers])


@app.route('/api/servers', methods=['POST'])
@login_required
def add_server():
    """Add a new server"""
    data = request.json

    required_fields = ['name', 'hostname', 'username', 'os_type']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    server = Server(
        name=data['name'],
        hostname=data['hostname'],
        port=data.get('port', 22),
        username=data['username'],
        ssh_key_path=data.get('ssh_key_path', ''),
        os_type=data['os_type']
    )

    db.session.add(server)
    db.session.commit()

    return jsonify(server.to_dict()), 201


@app.route('/api/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    """Update a server"""
    server = Server.query.get_or_404(server_id)
    data = request.json

    # Update fields
    if 'name' in data:
        server.name = data['name']
    if 'hostname' in data:
        server.hostname = data['hostname']
    if 'port' in data:
        server.port = data['port']
    if 'username' in data:
        server.username = data['username']
    if 'ssh_key_path' in data:
        server.ssh_key_path = data['ssh_key_path']
    if 'os_type' in data:
        server.os_type = data['os_type']

    db.session.commit()
    return jsonify(server.to_dict()), 200


@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    """Delete a server"""
    server = Server.query.get_or_404(server_id)
    db.session.delete(server)
    db.session.commit()
    return jsonify({'message': 'Server deleted successfully'}), 200


# ========== Server Provisioning Routes ==========

@app.route('/api/servers/provision', methods=['POST'])
@login_required
def provision_server():
    """Provision a new server with automated SSH setup"""
    data = request.json

    required_fields = ['name', 'hostname', 'port', 'root_username', 'root_password', 'os_type']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        provisioner = ServerProvisioner()

        # Provision the server
        result = provisioner.provision_server(
            hostname=data['hostname'],
            port=data['port'],
            root_username=data['root_username'],
            root_password=data['root_password'],
            os_type=data['os_type']
        )

        if not result['success']:
            return jsonify({
                'error': 'Provisioning failed',
                'details': result.get('error'),
                'steps': result.get('steps', [])
            }), 500

        # Create server entry with lum-user credentials
        server = Server(
            name=data['name'],
            hostname=data['hostname'],
            port=data['port'],
            username=result['username'],
            ssh_key_path=result['ssh_key_path'],
            os_type=data['os_type']
        )

        db.session.add(server)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Server provisioned and added successfully',
            'server': server.to_dict(),
            'provisioning_steps': result['steps']
        }), 201

    except Exception as e:
        return jsonify({
            'error': 'Provisioning failed',
            'message': str(e)
        }), 500


@app.route('/api/ssh-key', methods=['GET'])
@login_required
def get_ssh_key_info():
    """Get SSH key information"""
    try:
        provisioner = ServerProvisioner()
        info = provisioner.get_ssh_key_info()
        return jsonify(info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ssh-key/regenerate', methods=['POST'])
@login_required
def regenerate_ssh_key():
    """Regenerate SSH key pair"""
    try:
        provisioner = ServerProvisioner()
        private_key, public_key = provisioner.regenerate_ssh_key()

        return jsonify({
            'success': True,
            'message': 'SSH key regenerated successfully',
            'private_key_path': private_key,
            'public_key_path': public_key
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ssh-key/public', methods=['GET'])
@login_required
def get_public_key():
    """Get the public SSH key content"""
    try:
        provisioner = ServerProvisioner()
        public_key = provisioner.get_public_key()
        return jsonify({'public_key': public_key}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/servers/<int:server_id>/check', methods=['POST'])
@login_required
def check_updates(server_id):
    """Check for updates on a server"""
    server = Server.query.get_or_404(server_id)
    security_only = request.json.get('security_only', False) if request.json else False

    try:
        start_time = time.time()

        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None,
            password=None
        )

        connect_result = ssh.connect()
        if connect_result is not True:
            server.status = 'offline'
            db.session.commit()

            history = UpdateHistory(
                server_id=server.id,
                server_hostname=server.hostname,
                action='check',
                success=False,
                duration=time.time() - start_time,
                output=f"Connection failed: {connect_result[1]}"
            )
            db.session.add(history)
            db.session.commit()

            return jsonify({
                'error': 'Connection failed',
                'message': connect_result[1]
            }), 500

        server.status = 'online'

        update_manager = get_update_manager(server.os_type)
        result = update_manager.check_updates(ssh, security_only=security_only)

        ssh.disconnect()

        server.last_check = datetime.utcnow()
        server.updates_available = result['count']
        server.security_updates_count = result.get('security_count', 0)
        server.critical_cves_count = len(result.get('critical_cves', []))

        history = UpdateHistory(
            server_id=server.id,
            server_hostname=server.hostname,
            action='check',
            update_type='security' if security_only else 'all',
            packages_count=result['count'],
            package_list=json.dumps(result.get('packages', [])),
            security_count=result.get('security_count', 0),
            cve_list=json.dumps(result.get('cve_info', [])),
            critical_cves=json.dumps(result.get('critical_cves', [])),
            success=result['success'],
            duration=time.time() - start_time,
            output=result['output']
        )

        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'updates_available': result['count'],
            'packages': result.get('packages', []),
            'output': result['output']
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error checking updates for server {server_id}: {str(e)}\n{error_trace}")
        server.status = 'error'

        # Log error in history with full details
        error_output = f"Error: {str(e)}\n\nDetails:\n{error_trace}"
        history = UpdateHistory(
            server_id=server.id,
            server_hostname=server.hostname,
            action='check',
            success=False,
            duration=time.time() - start_time if 'start_time' in locals() else 0,
            output=error_output
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({
            'error': 'Error checking updates',
            'message': str(e)
        }), 500


@app.route('/api/servers/<int:server_id>/update', methods=['POST'])
@login_required
def apply_updates(server_id):
    """Apply updates on a server"""
    server = Server.query.get_or_404(server_id)
    security_only = request.json.get('security_only', False) if request.json else False
    auto_reboot = request.json.get('auto_reboot', True) if request.json else True

    try:
        start_time = time.time()

        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None,
            password=None
        )

        connect_result = ssh.connect()
        if connect_result is not True:
            server.status = 'offline'
            db.session.commit()

            return jsonify({
                'error': 'Connection failed',
                'message': connect_result[1]
            }), 500

        server.status = 'updating'
        db.session.commit()

        update_manager = get_update_manager(server.os_type)
        result = update_manager.apply_updates(ssh, security_only=security_only)

        # Check if reboot is needed
        reboot_required = False
        reboot_message = ''
        if result['success'] and auto_reboot:
            reboot_required = check_reboot_required(ssh, server.os_type)
            if reboot_required:
                reboot_result = reboot_server(ssh, delay_minutes=1)
                reboot_message = reboot_result['message'] if reboot_result['success'] else 'Failed to schedule reboot'

        ssh.disconnect()

        server.status = 'online'
        server.updates_available = 0
        server.last_check = datetime.utcnow()

        action = 'security_update' if security_only else 'update'

        # Add reboot info to output if applicable
        output = result['output']
        if reboot_required and reboot_message:
            output += f"\n\n=== REBOOT ===\n{reboot_message}"

        history = UpdateHistory(
            server_id=server.id,
            server_hostname=server.hostname,
            action=action,
            update_type='security' if security_only else 'all',
            packages_count=result['count'],
            package_list=json.dumps(result.get('packages', [])),
            success=result['success'],
            duration=time.time() - start_time,
            output=output
        )

        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'packages_updated': result['count'],
            'packages': result.get('packages', []),
            'reboot_required': reboot_required,
            'reboot_scheduled': reboot_required and auto_reboot,
            'reboot_message': reboot_message,
            'output': output
        })

    except Exception as e:
        server.status = 'error'
        db.session.commit()

        return jsonify({
            'error': 'Error applying updates',
            'message': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """Get update history"""
    server_id = request.args.get('server_id', type=int)

    query = UpdateHistory.query
    if server_id:
        query = query.filter_by(server_id=server_id)

    history = query.order_by(UpdateHistory.created_at.desc()).limit(100).all()
    return jsonify([h.to_dict() for h in history])


@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get statistics"""
    total_servers = Server.query.count()
    servers_with_updates = Server.query.filter(Server.updates_available > 0).count()
    total_updates = db.session.query(db.func.sum(Server.updates_available)).scalar() or 0

    # Count servers by status
    servers_online = Server.query.filter(Server.status == 'online').count()
    servers_offline = Server.query.filter(Server.status == 'offline').count()
    servers_updating = Server.query.filter(Server.status == 'updating').count()

    # Count servers by OS
    servers_debian = Server.query.filter(Server.os_type == 'debian').count()
    servers_almalinux = Server.query.filter(Server.os_type == 'almalinux').count()

    # Count scheduled updates
    total_schedules = ScheduledUpdate.query.count()
    enabled_schedules = ScheduledUpdate.query.filter(ScheduledUpdate.enabled == True).count()

    # Recent updates count
    from datetime import datetime, timedelta
    last_24h = datetime.utcnow() - timedelta(hours=24)
    updates_last_24h = UpdateHistory.query.filter(
        UpdateHistory.created_at >= last_24h,
        UpdateHistory.action.in_(['update', 'security_update'])
    ).count()

    # Security updates count
    security_updates_pending = db.session.query(Server).filter(Server.updates_available > 0).all()

    # CVE statistics
    servers_with_critical_cves = Server.query.filter(Server.critical_cves_count > 0).count()
    total_critical_cves = db.session.query(db.func.sum(Server.critical_cves_count)).scalar() or 0

    # Get servers with critical CVEs for alerts
    critical_servers = Server.query.filter(Server.critical_cves_count > 0).order_by(Server.critical_cves_count.desc()).limit(5).all()

    recent_history = UpdateHistory.query.order_by(UpdateHistory.created_at.desc()).limit(10).all()

    return jsonify({
        'total_servers': total_servers,
        'servers_with_updates': servers_with_updates,
        'total_updates': total_updates,
        'servers_online': servers_online,
        'servers_offline': servers_offline,
        'servers_updating': servers_updating,
        'servers_debian': servers_debian,
        'servers_almalinux': servers_almalinux,
        'total_schedules': total_schedules,
        'enabled_schedules': enabled_schedules,
        'updates_last_24h': updates_last_24h,
        'servers_with_critical_cves': servers_with_critical_cves,
        'total_critical_cves': total_critical_cves,
        'critical_servers': [s.to_dict() for s in critical_servers],
        'recent_activity': [h.to_dict() for h in recent_history]
    })


# ========== Scheduled Updates Routes ==========

@app.route('/api/servers/<int:server_id>/schedules', methods=['GET'])
@login_required
def get_server_schedules(server_id):
    """Get all schedules for a server"""
    server = Server.query.get_or_404(server_id)
    schedules = ScheduledUpdate.query.filter_by(server_id=server_id).all()
    return jsonify([s.to_dict() for s in schedules])


@app.route('/api/servers/<int:server_id>/schedules', methods=['POST'])
@login_required
def create_schedule(server_id):
    """Create a new update schedule for a server"""
    server = Server.query.get_or_404(server_id)
    data = request.json

    required_fields = ['schedule_type', 'hour']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate schedule type
    if data['schedule_type'] not in ['daily', 'weekly', 'monthly']:
        return jsonify({'error': 'Invalid schedule_type'}), 400

    # Validate day_of_week for weekly schedules
    if data['schedule_type'] == 'weekly' and 'day_of_week' not in data:
        return jsonify({'error': 'day_of_week required for weekly schedules'}), 400

    # Validate day_of_month for monthly schedules
    if data['schedule_type'] == 'monthly' and 'day_of_month' not in data:
        return jsonify({'error': 'day_of_month required for monthly schedules'}), 400

    schedule = ScheduledUpdate(
        server_id=server_id,
        enabled=data.get('enabled', True),
        schedule_type=data['schedule_type'],
        day_of_week=data.get('day_of_week'),
        day_of_month=data.get('day_of_month'),
        hour=data['hour'],
        minute=data.get('minute', 0),
        update_type=data.get('update_type', 'all'),
        auto_reboot=data.get('auto_reboot', False)
    )

    db.session.add(schedule)
    db.session.commit()

    # Configure automatic updates on the server
    try:
        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None,
            password=None
        )

        if not ssh.connect():
            return jsonify({
                'error': 'Failed to connect to server',
                'schedule': schedule.to_dict()
            }), 500

        configurator = AutoUpdateConfigurator()

        if server.os_type == 'debian':
            result = configurator.configure_debian_auto_updates(
                ssh, schedule, schedule.update_type, schedule.auto_reboot
            )
        else:  # almalinux
            result = configurator.configure_almalinux_auto_updates(
                ssh, schedule, schedule.update_type, schedule.auto_reboot
            )

        ssh.disconnect()

        if not result['success']:
            return jsonify({
                'error': 'Failed to configure automatic updates',
                'details': result.get('error'),
                'schedule': schedule.to_dict()
            }), 500

        return jsonify({
            'success': True,
            'schedule': schedule.to_dict(),
            'configuration': result
        }), 201

    except Exception as e:
        return jsonify({
            'error': 'Error configuring automatic updates',
            'message': str(e),
            'schedule': schedule.to_dict()
        }), 500


@app.route('/api/schedules/<int:schedule_id>', methods=['PUT'])
@login_required
def update_schedule(schedule_id):
    """Update an existing schedule"""
    schedule = ScheduledUpdate.query.get_or_404(schedule_id)
    data = request.json

    # Update fields
    if 'enabled' in data:
        schedule.enabled = data['enabled']
    if 'schedule_type' in data:
        schedule.schedule_type = data['schedule_type']
    if 'day_of_week' in data:
        schedule.day_of_week = data['day_of_week']
    if 'day_of_month' in data:
        schedule.day_of_month = data['day_of_month']
    if 'hour' in data:
        schedule.hour = data['hour']
    if 'minute' in data:
        schedule.minute = data['minute']
    if 'update_type' in data:
        schedule.update_type = data['update_type']
    if 'auto_reboot' in data:
        schedule.auto_reboot = data['auto_reboot']

    db.session.commit()

    # Reconfigure on the server
    server = schedule.server
    try:
        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None,
            password=None
        )

        if ssh.connect():
            configurator = AutoUpdateConfigurator()

            if server.os_type == 'debian':
                result = configurator.configure_debian_auto_updates(
                    ssh, schedule, schedule.update_type, schedule.auto_reboot
                )
            else:
                result = configurator.configure_almalinux_auto_updates(
                    ssh, schedule, schedule.update_type, schedule.auto_reboot
                )

            ssh.disconnect()

        return jsonify(schedule.to_dict()), 200

    except Exception as e:
        return jsonify({
            'error': 'Error updating configuration',
            'message': str(e)
        }), 500


@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_schedule(schedule_id):
    """Delete a schedule"""
    schedule = ScheduledUpdate.query.get_or_404(schedule_id)
    server = schedule.server

    db.session.delete(schedule)
    db.session.commit()

    # Remove configuration from server if it's the last schedule
    remaining_schedules = ScheduledUpdate.query.filter_by(server_id=server.id).count()
    if remaining_schedules == 0:
        try:
            ssh = SSHManager(
                hostname=server.hostname,
                port=server.port,
                username=server.username,
                ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
            )

            if ssh.connect():
                configurator = AutoUpdateConfigurator()
                configurator.remove_auto_updates(ssh, server.os_type)
                ssh.disconnect()

        except Exception as e:
            pass  # Don't fail if cleanup fails

    return jsonify({'message': 'Schedule deleted successfully'}), 200


@app.route('/api/servers/<int:server_id>/auto-update-status', methods=['GET'])
@login_required
def get_auto_update_status(server_id):
    """Check automatic update configuration status on a server"""
    server = Server.query.get_or_404(server_id)

    try:
        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None,
            password=None
        )

        if not ssh.connect():
            return jsonify({'error': 'Failed to connect to server'}), 500

        configurator = AutoUpdateConfigurator()
        status = configurator.get_auto_update_status(ssh, server.os_type)
        ssh.disconnect()

        return jsonify(status), 200

    except Exception as e:
        return jsonify({
            'error': 'Error checking status',
            'message': str(e)
        }), 500


# ==================== Auto-Check Management Routes ====================

@app.route('/api/servers/<int:server_id>/auto-check', methods=['PUT'])
@login_required
def toggle_auto_check(server_id):
    """Enable or disable automatic update checking for a server"""
    server = Server.query.get_or_404(server_id)
    data = request.json

    try:
        server.auto_check = data.get('auto_check', server.auto_check)
        server.check_interval = data.get('check_interval', server.check_interval)

        db.session.commit()

        # Update scheduler job
        if server.auto_check:
            update_scheduler.add_server_job(server.id, server.check_interval)
        else:
            update_scheduler.remove_server_job(server.id)

        return jsonify({
            'success': True,
            'message': f"Auto-check {'enabled' if server.auto_check else 'disabled'} for {server.name}",
            'server': server.to_dict()
        })

    except Exception as e:
        logger.error(f"Error toggling auto-check: {str(e)}")
        return jsonify({
            'error': 'Error updating auto-check settings',
            'message': str(e)
        }), 500


@app.route('/api/scheduler/jobs', methods=['GET'])
@login_required
def get_scheduler_jobs():
    """Get list of scheduled jobs"""
    try:
        jobs = update_scheduler.get_jobs()
        return jsonify(jobs), 200
    except Exception as e:
        return jsonify({
            'error': 'Error getting scheduler jobs',
            'message': str(e)
        }), 500


@app.route('/api/scheduler/trigger', methods=['POST'])
@login_required
def trigger_check_now():
    """Manually trigger update check for all servers"""
    try:
        update_scheduler.check_all_servers()
        return jsonify({
            'success': True,
            'message': 'Update check triggered for all servers'
        })
    except Exception as e:
        logger.error(f"Error triggering manual check: {str(e)}")
        return jsonify({
            'error': 'Error triggering check',
            'message': str(e)
        }), 500


@app.route('/api/schedules', methods=['GET'])
@login_required
def get_all_schedules():
    """Get all scheduled updates"""
    schedules = ScheduledUpdate.query.all()
    return jsonify([s.to_dict() for s in schedules]), 200


# Initialize database and start scheduler
with app.app_context():
    db.create_all()

    # Create default admin user if doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin user")

    # Start the update scheduler
    update_scheduler.start()
    logger.info("Update scheduler started")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
