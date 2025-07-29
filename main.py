#!/usr/bin/env python3
"""
IronLock Vault - Secure Desktop Vault Application
Main entry point for the application
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import threading
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui import VaultUI
from auth import AuthManager
from vault import VaultManager
from logger import VaultLogger
from config import Config
from encryption import EncryptionManager

class IronLockVault:
    def __init__(self):
        self.config = Config()
        self.logger = VaultLogger()
        self.auth_manager = AuthManager(self.config, self.logger)
        self.encryption_manager = EncryptionManager(self.config)
        self.vault_manager = VaultManager(self.config, self.logger, self.encryption_manager)
        
        # Initialize UI
        self.root = tk.Tk()
        self.ui = VaultUI(
            self.root, 
            self.auth_manager, 
            self.vault_manager, 
            self.config, 
            self.logger,
            self  # Pass reference to main application
        )
        
        # Check if this is first-time setup
        if self.is_first_time_setup():
            self.show_first_time_setup()
        else:
            # Setup auto-lock timer
            self.last_activity = time.time()
            self.auto_lock_thread = None
            self.start_auto_lock_monitor()
            
            # Setup global hotkey for quick lock
            self.setup_hotkeys()
    
    def is_first_time_setup(self):
        """Check if this is the first time the application is being run"""
        # Check if any users exist in the database
        try:
            conn = self.auth_manager.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            conn.close()
            
            # Also check if setup is marked as complete
            setup_complete = self.config.get('setup_complete', False)
            
            return user_count == 0 and not setup_complete
        except Exception as e:
            self.logger.log_error(f"Error checking first-time setup: {str(e)}")
            return True
    
    def show_first_time_setup(self):
        """Show the first-time setup wizard"""
        self.ui.show_first_time_setup_wizard()
        
    def start_auto_lock_monitor(self):
        """Start the auto-lock monitoring thread"""
        def monitor():
            while True:
                if hasattr(self.ui, 'is_logged_in') and self.ui.is_logged_in:
                    timeout = self.config.get('auto_lock_timeout', 300)
                    time_since_activity = time.time() - self.last_activity
                    
                    # Log debug info every 30 seconds
                    if int(time.time()) % 30 == 0:
                        self.logger.log_info(f"Auto-lock monitor: {time_since_activity:.1f}s since last activity, timeout: {timeout}s")
                    
                    if timeout is not None and time_since_activity > timeout:
                        self.logger.log_info(f"Auto-lock triggered after {time_since_activity:.1f}s of inactivity")
                        self.root.after(0, self.ui.auto_lock)
                        # Reset activity time after auto-lock to prevent immediate re-lock
                        self.last_activity = time.time()
                time.sleep(10)
        
        self.auto_lock_thread = threading.Thread(target=monitor, daemon=True)
        self.auto_lock_thread.start()
        self.logger.log_info("Auto-lock monitoring started")
    
    def setup_hotkeys(self):
        """Setup global hotkeys"""
        def on_activity(event=None):
            self.last_activity = time.time()
        
        # Bind activity events
        self.root.bind('<Motion>', on_activity)
        self.root.bind('<Key>', on_activity)
        self.root.bind('<Button>', on_activity)
        
        # Quick lock hotkey (Ctrl+Shift+L)
        def quick_lock(event=None):
            if hasattr(self.ui, 'is_logged_in') and self.ui.is_logged_in:
                self.ui.lock_vault()
        
        self.root.bind('<Control-Shift-L>', quick_lock)
    
    def run(self):
        """Start the application"""
        try:
            self.logger.log_info("IronLock Vault started")
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            self.logger.log_error(f"Application error: {str(e)}")
            messagebox.showerror("Error", f"Application error: {str(e)}")
    
    def on_closing(self):
        """Handle application closing"""
        if hasattr(self.ui, 'is_logged_in') and self.ui.is_logged_in:
            if messagebox.askokcancel("Quit", "Do you want to lock the vault and quit?"):
                self.ui.lock_vault()
                self.logger.log_info("IronLock Vault closed")
                self.root.destroy()
        else:
            self.logger.log_info("IronLock Vault closed")
            self.root.destroy()
    
    def set_auto_lock_timeout(self, timeout_seconds):
        """Set auto-lock timeout for testing purposes"""
        self.config.set('auto_lock_timeout', timeout_seconds)
        print(f"Auto-lock timeout set to {timeout_seconds} seconds")

if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("vault", exist_ok=True)
    
    app = IronLockVault()
    app.run()
