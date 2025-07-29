"""
Logging and alerting system for IronLock Vault
"""

import logging
import json
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class VaultLogger:
    def __init__(self, log_directory="logs"):
        self.log_directory = log_directory
        os.makedirs(log_directory, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Alert thresholds
        self.alert_thresholds = {
            'failed_logins': 5,
            'suspicious_access': 3,
            'tamper_attempts': 1
        }
        
        # Alert counters
        self.alert_counters = {
            'failed_logins': 0,
            'suspicious_access': 0,
            'tamper_attempts': 0
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup main logger
        self.logger = logging.getLogger('IronLockVault')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler for all logs
        log_file = os.path.join(self.log_directory, 'vault.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # File handler for security events
        security_log_file = os.path.join(self.log_directory, 'security.log')
        self.security_handler = logging.FileHandler(security_log_file)
        self.security_handler.setLevel(logging.WARNING)
        self.security_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def log_info(self, message):
        """Log info message"""
        self.logger.info(message)
        self._save_to_json_log('INFO', message)
    
    def log_warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
        self.security_handler.handle(self.logger.makeRecord(
            'IronLockVault', logging.WARNING, '', 0, message, (), None
        ))
        self._save_to_json_log('WARNING', message)
        self._check_alert_thresholds('suspicious_access')
    
    def log_error(self, message):
        """Log error message"""
        self.logger.error(message)
        self.security_handler.handle(self.logger.makeRecord(
            'IronLockVault', logging.ERROR, '', 0, message, (), None
        ))
        self._save_to_json_log('ERROR', message)
    
    def log_security_event(self, event_type, message, severity='HIGH'):
        """Log security event"""
        security_message = f"SECURITY [{severity}] {event_type}: {message}"
        self.logger.critical(security_message)
        self.security_handler.handle(self.logger.makeRecord(
            'IronLockVault', logging.CRITICAL, '', 0, security_message, (), None
        ))
        
        self._save_to_json_log('SECURITY', security_message, {
            'event_type': event_type,
            'severity': severity
        })
        
        # Check for alerts
        if event_type == 'failed_login':
            self._check_alert_thresholds('failed_logins')
        elif event_type == 'tamper_attempt':
            self._check_alert_thresholds('tamper_attempts')
    
    def _save_to_json_log(self, level, message, extra_data=None):
        """Save log entry to JSON file"""
        try:
            json_log_file = os.path.join(self.log_directory, 'vault_logs.json')
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message
            }
            
            if extra_data:
                log_entry.update(extra_data)
            
            # Read existing logs
            logs = []
            if os.path.exists(json_log_file):
                try:
                    with open(json_log_file, 'r') as f:
                        logs = json.load(f)
                except json.JSONDecodeError:
                    logs = []
            
            # Add new log entry
            logs.append(log_entry)
            
            # Keep only recent logs (last 1000 entries)
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # Save back to file
            with open(json_log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save JSON log: {str(e)}")
    
    def _check_alert_thresholds(self, alert_type):
        """Check if alert thresholds are exceeded"""
        self.alert_counters[alert_type] += 1
        
        if self.alert_counters[alert_type] >= self.alert_thresholds[alert_type]:
            self._send_alert(alert_type, self.alert_counters[alert_type])
            # Reset counter after alert
            self.alert_counters[alert_type] = 0
    
    def _send_alert(self, alert_type, count):
        """Send security alert"""
        alert_message = f"SECURITY ALERT: {alert_type} threshold exceeded ({count} occurrences)"
        
        # Log the alert
        self.log_security_event('security_alert', alert_message, 'CRITICAL')
        
        # In production, send email/SMS/push notification
        print(f"🚨 {alert_message}")
    
    def get_recent_logs(self, hours=24, level=None):
        """Get recent log entries"""
        try:
            json_log_file = os.path.join(self.log_directory, 'vault_logs.json')
            
            if not os.path.exists(json_log_file):
                return []
            
            with open(json_log_file, 'r') as f:
                logs = json.load(f)
            
            # Filter by time
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_logs = []
            
            for log in logs:
                log_time = datetime.fromisoformat(log['timestamp'])
                if log_time >= cutoff_time:
                    if level is None or log['level'] == level:
                        recent_logs.append(log)
            
            return recent_logs
            
        except Exception as e:
            self.logger.error(f"Error getting recent logs: {str(e)}")
            return []
    
    def get_security_summary(self):
        """Get security summary"""
        try:
            security_logs = self.get_recent_logs(hours=24, level='SECURITY')
            
            summary = {
                'total_security_events': len(security_logs),
                'failed_logins': len([log for log in security_logs if 'failed_login' in log.get('event_type', '')]),
                'tamper_attempts': len([log for log in security_logs if 'tamper_attempt' in log.get('event_type', '')]),
                'suspicious_access': len([log for log in security_logs if 'suspicious_access' in log.get('message', '')]),
                'last_24h_events': security_logs[-10:]  # Last 10 events
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting security summary: {str(e)}")
            return {}
    
    def cleanup_old_logs(self, days=30):
        """Cleanup old log files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for filename in os.listdir(self.log_directory):
                file_path = os.path.join(self.log_directory, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        self.log_info(f"Cleaned up old log file: {filename}")
                        
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {str(e)}")
