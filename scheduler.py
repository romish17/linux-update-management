"""
Automatic Update Check Scheduler
Periodically checks for updates on configured servers
"""

import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

logger = logging.getLogger(__name__)


class UpdateScheduler:
    """Manage automatic update checking for servers"""

    def __init__(self, app=None, db=None):
        self.scheduler = BackgroundScheduler()
        self.app = app
        self.db = db
        self.is_running = False

    def init_app(self, app, db):
        """Initialize scheduler with Flask app and database"""
        self.app = app
        self.db = db

    def start(self):
        """Start the background scheduler"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Update scheduler started")

            # Add default job to check all servers every 6 hours
            self.scheduler.add_job(
                func=self.check_all_servers,
                trigger=IntervalTrigger(hours=6),
                id='check_all_servers',
                name='Check all servers for updates',
                replace_existing=True
            )

    def stop(self):
        """Stop the background scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Update scheduler stopped")

    def check_all_servers(self):
        """Check all servers with auto_check enabled"""
        if not self.app or not self.db:
            logger.error("Scheduler not properly initialized")
            return

        with self.app.app_context():
            from models import Server
            from ssh_manager import SSHManager, get_update_manager

            servers = Server.query.filter_by(auto_check=True).all()
            logger.info(f"Checking {len(servers)} servers for updates")

            for server in servers:
                try:
                    self._check_server_updates(server)
                except Exception as e:
                    logger.error(f"Error checking server {server.name}: {str(e)}")

            self.db.session.commit()

    def _check_server_updates(self, server):
        """Check updates for a specific server"""
        from models import UpdateHistory
        import json

        start_time = time.time()

        try:
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
                logger.warning(f"Server {server.name} is offline")
                return

            server.status = 'online'

            # Check for updates (including security updates)
            update_manager = get_update_manager(server.os_type)
            result = update_manager.check_updates(ssh, security_only=False)

            ssh.disconnect()

            # Update server info
            server.last_check = datetime.now()
            server.updates_available = result['count']

            # Log to history
            history = UpdateHistory(
                server_id=server.id,
                server_hostname=server.hostname,
                action='auto_check',
                update_type='all',
                packages_count=result['count'],
                package_list=json.dumps(result.get('packages', [])),
                success=result['success'],
                duration=time.time() - start_time,
                output=f"Automatic check: {result['count']} updates available"
            )

            self.db.session.add(history)
            logger.info(f"Server {server.name}: {result['count']} updates available")

        except Exception as e:
            logger.error(f"Error checking server {server.name}: {str(e)}")
            server.status = 'error'

            # Log error to history
            history = UpdateHistory(
                server_id=server.id,
                server_hostname=server.hostname,
                action='auto_check',
                success=False,
                duration=time.time() - start_time,
                output=f"Error: {str(e)}"
            )
            self.db.session.add(history)

    def add_server_job(self, server_id, interval_hours=6):
        """Add a scheduled job for a specific server"""
        job_id = f'check_server_{server_id}'

        self.scheduler.add_job(
            func=self._check_single_server,
            args=[server_id],
            trigger=IntervalTrigger(hours=interval_hours),
            id=job_id,
            name=f'Check server {server_id}',
            replace_existing=True
        )

        logger.info(f"Added job for server {server_id} (every {interval_hours}h)")

    def remove_server_job(self, server_id):
        """Remove scheduled job for a specific server"""
        job_id = f'check_server_{server_id}'

        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job for server {server_id}")
        except Exception as e:
            logger.warning(f"Could not remove job {job_id}: {str(e)}")

    def _check_single_server(self, server_id):
        """Check updates for a single server by ID"""
        if not self.app or not self.db:
            return

        with self.app.app_context():
            from models import Server

            server = Server.query.get(server_id)
            if server and server.auto_check:
                self._check_server_updates(server)
                self.db.session.commit()

    def get_jobs(self):
        """Get list of scheduled jobs"""
        return [{
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        } for job in self.scheduler.get_jobs()]


# Global scheduler instance
update_scheduler = UpdateScheduler()
