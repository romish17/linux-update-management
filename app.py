from flask import Flask, render_template, request, jsonify
from datetime import datetime
from config import Config
from models import db, Server, UpdateHistory
from ssh_manager import SSHManager, get_update_manager
import os

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

    try:
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
                action='check',
                success=False,
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
        result = update_manager.check_updates(ssh)

        ssh.disconnect()

        server.last_check = datetime.utcnow()
        server.updates_available = result['count']

        history = UpdateHistory(
            server_id=server.id,
            action='check',
            packages_count=result['count'],
            success=result['success'],
            output=result['output']
        )

        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'updates_available': result['count'],
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

    try:
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
        result = update_manager.apply_updates(ssh)

        ssh.disconnect()

        server.status = 'online'
        server.updates_available = 0
        server.last_check = datetime.utcnow()

        history = UpdateHistory(
            server_id=server.id,
            action='update',
            packages_count=result['count'],
            success=result['success'],
            output=result['output']
        )

        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'packages_updated': result['count'],
            'output': result['output']
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
