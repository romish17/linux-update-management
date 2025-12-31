from flask import Flask, render_template, request, jsonify
from datetime import datetime
from config import Config
from models import db, Server, UpdateHistory, ScheduledUpdate
from ssh_manager import SSHManager, get_update_manager, check_reboot_required, reboot_server
from auto_update_manager import AutoUpdateConfigurator
import os
import json
import time

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/servers', methods=['GET'])
def get_servers():
    """Get all servers"""
    servers = Server.query.all()
    return jsonify([server.to_dict() for server in servers])


@app.route('/api/servers', methods=['POST'])
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


@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    """Delete a server"""
    server = Server.query.get_or_404(server_id)
    db.session.delete(server)
    db.session.commit()
    return jsonify({'message': 'Server deleted successfully'}), 200


@app.route('/api/servers/<int:server_id>/check', methods=['POST'])
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
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
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

        history = UpdateHistory(
            server_id=server.id,
            server_hostname=server.hostname,
            action='check',
            update_type='security' if security_only else 'all',
            packages_count=result['count'],
            package_list=json.dumps(result.get('packages', [])),
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
        server.status = 'error'
        db.session.commit()

        return jsonify({
            'error': 'Error checking updates',
            'message': str(e)
        }), 500


@app.route('/api/servers/<int:server_id>/update', methods=['POST'])
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
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
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
def get_history():
    """Get update history"""
    server_id = request.args.get('server_id', type=int)

    query = UpdateHistory.query
    if server_id:
        query = query.filter_by(server_id=server_id)

    history = query.order_by(UpdateHistory.created_at.desc()).limit(100).all()
    return jsonify([h.to_dict() for h in history])


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics"""
    total_servers = Server.query.count()
    servers_with_updates = Server.query.filter(Server.updates_available > 0).count()
    total_updates = db.session.query(db.func.sum(Server.updates_available)).scalar() or 0
    recent_history = UpdateHistory.query.order_by(UpdateHistory.created_at.desc()).limit(10).all()

    return jsonify({
        'total_servers': total_servers,
        'servers_with_updates': servers_with_updates,
        'total_updates': total_updates,
        'recent_activity': [h.to_dict() for h in recent_history]
    })


# ========== Scheduled Updates Routes ==========

@app.route('/api/servers/<int:server_id>/schedules', methods=['GET'])
def get_server_schedules(server_id):
    """Get all schedules for a server"""
    server = Server.query.get_or_404(server_id)
    schedules = ScheduledUpdate.query.filter_by(server_id=server_id).all()
    return jsonify([s.to_dict() for s in schedules])


@app.route('/api/servers/<int:server_id>/schedules', methods=['POST'])
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
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
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
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
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
def get_auto_update_status(server_id):
    """Check automatic update configuration status on a server"""
    server = Server.query.get_or_404(server_id)

    try:
        ssh = SSHManager(
            hostname=server.hostname,
            port=server.port,
            username=server.username,
            ssh_key_path=server.ssh_key_path if server.ssh_key_path else None
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
