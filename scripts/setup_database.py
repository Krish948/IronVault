#!/usr/bin/env python3
"""
Database setup and management script for IronLock Vault
"""

import sys
import os
import sqlite3
import json

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

def reset_first_time_setup():
    """Reset the first-time setup flag for testing"""
    config = Config()
    
    # Remove setup_complete flag
    config.set('setup_complete', False)
    
    # Clear user database
    db_path = "data/users.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print("User database cleared.")
    
    print("First-time setup flag reset. The app will show the setup wizard on next launch.")

def show_database_info():
    """Show information about the current database"""
    db_path = "data/users.db"
    
    if not os.path.exists(db_path):
        print("No user database found.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get user count
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    print(f"User database found: {db_path}")
    print(f"Total users: {user_count}")
    
    if user_count > 0:
        # Get user list
        cursor.execute("SELECT username, email, mobile_number, created_at, last_login FROM users")
        users = cursor.fetchall()
        
        print("\nUsers:")
        for user in users:
            username, email, mobile_number, created, last_login = user
            print(f"  - {username}")
            print(f"    Email: {email or 'No email'}")
            print(f"    Mobile: {mobile_number or 'No mobile'}")
            print(f"    Created: {created}")
            print(f"    Last login: {last_login or 'Never'}")
    
    conn.close()

def main():
    """Main function"""
    print("IronLock Vault Database Management")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Reset first-time setup (clear all users)")
        print("2. Show database information")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            confirm = input("This will delete all users and reset setup. Continue? (y/N): ").strip().lower()
            if confirm == 'y':
                reset_first_time_setup()
            else:
                print("Operation cancelled.")
        
        elif choice == "2":
            show_database_info()
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
