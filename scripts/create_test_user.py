#!/usr/bin/env python3
"""
Create a test user for OTP testing
"""

import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth import AuthManager
from config import Config
from logger import VaultLogger

def create_test_user():
    """Create a test user with email and mobile number"""
    config = Config()
    logger = VaultLogger()
    auth_manager = AuthManager(config, logger)
    
    # Test user data
    username = "testuser"
    password = "TestPassword123!"
    email = "test@example.com"
    mobile_number = "+1234567890"
    
    # Check if user already exists
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        print(f"User '{username}' already exists.")
        conn.close()
        return
    
    conn.close()
    
    # Register the test user
    success, message = auth_manager.register_user(
        username=username,
        password=password,
        email=email,
        mobile_number=mobile_number,
        user_data={"full_name": "Test User", "organization": "Test Org"}
    )
    
    if success:
        print(f"Test user created successfully!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Email: {email}")
        print(f"Mobile: {mobile_number}")
        print("\nYou can now test the OTP login functionality.")
    else:
        print(f"Failed to create test user: {message}")

if __name__ == "__main__":
    create_test_user() 