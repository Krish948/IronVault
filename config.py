"""
Configuration management for IronLock Vault
"""

import json
import os
from pathlib import Path

class Config:
    def __init__(self, config_file="data/config.json"):
        self.config_file = config_file
        self.default_config = {
            "app_name": "IronLock Vault",
            "version": "1.0.0",
            "auto_lock_timeout": 300,  # 5 minutes
            "max_login_attempts": 3,
            "encryption_algorithm": "fernet",
            "email_smtp_server": "smtp.gmail.com",
            "email_smtp_port": 587,
            "log_retention_days": 30,
            "theme": "darkly",
            "window_size": "1200x800",
            "enable_biometric": False,
            "enable_email_alerts": False,
            "enable_sms_otp": False,
            "twilio_account_sid": "",
            "twilio_auth_token": "",
            "twilio_phone_number": "",
            "vault_directory": "vault",
            "backup_enabled": True,
            "backup_interval": 24,  # hours
        }
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults for any missing keys
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates):
        """Update multiple configuration values"""
        self.config.update(updates)
        self.save_config()
