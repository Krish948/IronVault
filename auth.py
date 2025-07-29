"""
Authentication and 2FA management for IronLock Vault
"""

import json
import os
import sqlite3
import secrets
import string
import smtplib
import pyotp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import hashlib
import base64
import binascii

# Import Twilio for SMS OTP (optional - will handle gracefully if not available)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

class AuthManager:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.db_path = "data/users.db"
        self.init_database()
        self.current_user = None
        self.login_attempts = {}
    
    def init_database(self):
        """Initialize user database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                email TEXT,
                mobile_number TEXT,
                user_data TEXT,
                encryption_salt TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Remove totp_secret column if it exists (migration)
        try:
            cursor.execute("ALTER TABLE users DROP COLUMN totp_secret")
        except sqlite3.OperationalError:
            pass
        
        # Add user_data column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN user_data TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add encryption_salt column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN encryption_salt TEXT")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT,
                success BOOLEAN NOT NULL,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                failure_reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_user(self, username, password, email=None, mobile_number=None, user_data=None, enable_2fa=True):
        """Register a new user with additional data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, "Username already exists"
            
            # Check if mobile number already exists (if provided)
            if mobile_number:
                cursor.execute("SELECT username FROM users WHERE mobile_number = ?", (mobile_number,))
                if cursor.fetchone():
                    return False, "Mobile number already registered"
            
            # Hash password
            salt_bytes = os.urandom(16)
            salt = base64.b64encode(salt_bytes).decode()
            password_hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
            password_hash = base64.b64encode(password_hash_bytes).decode()
            
            # Generate encryption salt for vault encryption
            encryption_salt_bytes = os.urandom(16)
            encryption_salt = base64.b64encode(encryption_salt_bytes).decode()
            
            # Store additional user data as JSON
            user_data_json = json.dumps(user_data) if user_data else None
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, email, mobile_number, user_data, encryption_salt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, salt, email, mobile_number, user_data_json, encryption_salt))
            
            conn.commit()
            conn.close()
            
            self.logger.log_info(f"User registered: {username} (2FA: {'enabled' if enable_2fa else 'disabled'})")
            return True, "User registered successfully"
            
        except Exception as e:
            self.logger.log_error(f"Registration error: {str(e)}")
            return False, f"Registration failed: {str(e)}"
    
    def authenticate_user(self, username, password):
        """Authenticate user with username and password"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT password_hash, salt, email, mobile_number, is_active, encryption_salt 
                FROM users WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                self.log_login_attempt(username, False, "User not found")
                return False, "Invalid credentials"
            
            password_hash, salt, email, mobile_number, is_active, encryption_salt = result
            
            if not is_active:
                self.log_login_attempt(username, False, "Account disabled")
                return False, "Account is disabled"
            
            # Handle both old (bytes) and new (base64 string) formats
            try:
                # Try new format first (base64 strings)
                if isinstance(salt, bytes):
                    salt = salt.decode()
                if isinstance(password_hash, bytes):
                    password_hash = password_hash.decode()
                
                salt_bytes = base64.b64decode(salt)
                password_hash_bytes = base64.b64decode(password_hash)
                
            except (UnicodeDecodeError, binascii.Error):
                # Fall back to old format (raw bytes)
                if isinstance(salt, str):
                    salt = salt.encode()
                if isinstance(password_hash, str):
                    password_hash = password_hash.encode()
                
                salt_bytes = salt
                password_hash_bytes = password_hash
            
            # Verify password
            test_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt_bytes, 100000)
            
            if test_hash == password_hash_bytes:
                self.current_user = {
                    'username': username,
                    'email': email,
                    'mobile_number': mobile_number,
                    'encryption_salt': encryption_salt
                }
                return True, "Authentication successful"
            else:
                self.log_login_attempt(username, False, "Invalid password")
                return False, "Invalid credentials"
                
        except Exception as e:
            self.logger.log_error(f"Authentication error: {str(e)}")
            return False, f"Authentication failed: {str(e)}"
    
    def verify_totp(self, token):
        """Verify TOTP token"""
        if not self.current_user:
            return False
        
        # TOTP verification is removed, so this method is no longer functional
        # For now, it will always return False as TOTP is disabled.
        # If 2FA is re-introduced, this method needs to be reimplemented.
        return False
    
    def generate_email_otp(self):
        """Generate and send email OTP"""
        if not self.current_user or not self.current_user.get('email'):
            return False, "No email configured"
        
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Store OTP temporarily (in production, use Redis or similar)
        self.current_otp = {
            'code': otp,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        try:
            # Send email OTP
            self.send_email_otp(self.current_user['email'], otp)
            return True, "OTP sent successfully"
            
        except Exception as e:
            self.logger.log_error(f"Email OTP error: {str(e)}")
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_email_otp(self, otp):
        """Verify email OTP"""
        if not hasattr(self, 'current_otp'):
            return False
        
        if datetime.now() > self.current_otp['expires']:
            return False
        
        return self.current_otp['code'] == otp
    
    def generate_mobile_otp(self):
        """Generate and send mobile OTP via SMS"""
        if not self.current_user or not self.current_user.get('mobile_number'):
            return False, "No mobile number configured"
        
        otp = ''.join(secrets.choice(string.digits) for _ in range(6))
        
        # Store OTP temporarily (in production, use Redis or similar)
        self.current_otp = {
            'code': otp,
            'expires': datetime.now() + timedelta(minutes=5)
        }
        
        try:
            # Send SMS OTP
            self.send_sms_otp(self.current_user['mobile_number'], otp)
            return True, "OTP sent successfully"
            
        except Exception as e:
            self.logger.log_error(f"Mobile OTP error: {str(e)}")
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_mobile_otp(self, otp):
        """Verify mobile OTP"""
        if not hasattr(self, 'current_otp'):
            return False
        
        if datetime.now() > self.current_otp['expires']:
            return False
        
        return self.current_otp['code'] == otp
    
    def send_sms_otp(self, mobile_number, otp):
        """Send OTP via SMS using Twilio"""
        if not TWILIO_AVAILABLE:
            self.logger.log_warning("Twilio library not available - SMS OTP disabled")
            print("Demo Mode - SMS OTP: {otp}")
            print("To enable SMS delivery, install twilio: pip install twilio")
            return
        
        account_sid = self.config.get('twilio_account_sid')
        auth_token = self.config.get('twilio_auth_token')
        from_number = self.config.get('twilio_phone_number')
        
        # Check if Twilio credentials are configured
        if not all([account_sid, auth_token, from_number]):
            # Fallback to demo mode
            self.logger.log_info(f"SMS OTP for {self.current_user['username']}: {otp}")
            print(f"Demo Mode - SMS OTP: {otp}")
            print("To enable real SMS delivery, configure Twilio credentials in config.json")
            return
        
        try:
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=f"Your IronLock Vault access code is: {otp}. This code expires in 5 minutes.",
                from_=from_number,
                to=mobile_number
            )
            
            self.logger.log_info(f"SMS sent to {mobile_number}: {message.sid}")
            
        except Exception as e:
            self.logger.log_error(f"SMS sending failed: {str(e)}")
            # Fallback to demo mode
            self.logger.log_info(f"SMS OTP for {self.current_user['username']}: {otp}")
            print(f"Demo Mode - SMS OTP: {otp}")
            print(f"SMS sending failed: {str(e)}")
    
    def send_email_otp(self, email, otp):
        """Send OTP via email"""
        smtp_server = self.config.get('email_smtp_server')
        smtp_port = self.config.get('email_smtp_port')
        email_username = self.config.get('email_username')
        email_password = self.config.get('email_password')
        
        # Check if email credentials are configured
        if not email_username or not email_password:
            # Fallback to demo mode
            self.logger.log_info(f"Email OTP for {self.current_user['username']}: {otp}")
            print(f"Demo Mode - Email OTP: {otp}")
            print("To enable real email delivery, configure email_username and email_password in config.json")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = email_username
            msg['To'] = email
            msg['Subject'] = "IronLock Vault - Access Code"
            
            body = f"""
            Your IronLock Vault access code is: {otp}
            
            This code will expire in 5 minutes.
            
            If you didn't request this code, please secure your account immediately.
            
            Best regards,
            IronLock Vault Security Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email using configured SMTP
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_username, email_password)
            server.send_message(msg)
            server.quit()
            
            self.logger.log_info(f"Email OTP sent to {email}")
            
        except Exception as e:
            self.logger.log_error(f"Email sending failed: {str(e)}")
            # Fallback to demo mode
            self.logger.log_info(f"Email OTP for {self.current_user['username']}: {otp}")
            print(f"Demo Mode - Email OTP: {otp}")
            print(f"Email sending failed: {str(e)}")
    
    def log_login_attempt(self, username, success, failure_reason=None):
        """Log login attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO login_attempts (username, success, failure_reason)
                VALUES (?, ?, ?)
            ''', (username, success, failure_reason))
            
            conn.commit()
            conn.close()
            
            if success:
                self.logger.log_info(f"Successful login: {username}")
            else:
                self.logger.log_warning(f"Failed login attempt: {username} - {failure_reason}")
                
        except Exception as e:
            self.logger.log_error(f"Error logging login attempt: {str(e)}")
    
    def update_last_login(self, username):
        """Update last login timestamp"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE username = ?
            ''', (username,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.log_error(f"Error updating last login: {str(e)}")
    
    def get_login_history(self, username=None, limit=50):
        """Get login history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if username:
                cursor.execute('''
                    SELECT username, success, attempt_time, failure_reason
                    FROM login_attempts 
                    WHERE username = ?
                    ORDER BY attempt_time DESC 
                    LIMIT ?
                ''', (username, limit))
            else:
                cursor.execute('''
                    SELECT username, success, attempt_time, failure_reason
                    FROM login_attempts 
                    ORDER BY attempt_time DESC 
                    LIMIT ?
                ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return results
            
        except Exception as e:
            self.logger.log_error(f"Error getting login history: {str(e)}")
            return []
    
    def logout(self):
        """Logout current user"""
        if self.current_user:
            self.logger.log_info(f"User logged out: {self.current_user['username']}")
            self.current_user = None
            if hasattr(self, 'current_otp'):
                delattr(self, 'current_otp')
    
    def validate_mobile_number(self, mobile_number):
        """Validate mobile number format"""
        if not mobile_number:
            return True, "Mobile number is optional"
        
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, mobile_number))
        
        # Check if it's a valid length (7-15 digits for international numbers)
        if len(digits_only) < 7 or len(digits_only) > 15:
            return False, "Mobile number must be 7-15 digits long"
        
        # Check if it contains only digits and common separators
        allowed_chars = set('0123456789+-() .')
        if not all(c in allowed_chars for c in mobile_number):
            return False, "Mobile number contains invalid characters"
        
        return True, "Mobile number is valid"
    
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def enable_2fa_for_user(self, username):
        """Enable 2FA for an existing user by generating a TOTP secret"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT totp_secret FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return False, "User not found"
            
            # Check if 2FA is already enabled
            if result[0] is not None:
                conn.close()
                return False, "2FA is already enabled for this user"
            
            # Generate new TOTP secret
            totp_secret = pyotp.random_base32()
            
            # Update user record
            cursor.execute("UPDATE users SET totp_secret = ? WHERE username = ?", (totp_secret, username))
            conn.commit()
            conn.close()
            
            # Update current user if it's the same user
            if self.current_user and self.current_user['username'] == username:
                self.current_user['totp_secret'] = totp_secret
            
            self.logger.log_info(f"2FA enabled for user: {username}")
            return True, "2FA enabled successfully"
            
        except Exception as e:
            self.logger.log_error(f"Error enabling 2FA: {str(e)}")
            return False, f"Failed to enable 2FA: {str(e)}"
    
    def verify_current_password(self, username, current_password):
        """Verify the current password for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT password_hash, salt FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False, "User not found"
            
            stored_hash, salt = result
            
            # Handle both old (bytes) and new (base64 string) formats
            try:
                # Try new format first (base64 strings)
                if isinstance(salt, bytes):
                    salt = salt.decode()
                if isinstance(stored_hash, bytes):
                    stored_hash = stored_hash.decode()
                
                salt_bytes = base64.b64decode(salt)
                stored_hash_bytes = base64.b64decode(stored_hash)
                
            except (UnicodeDecodeError, binascii.Error):
                # Fall back to old format (raw bytes)
                if isinstance(salt, str):
                    salt = salt.encode()
                if isinstance(stored_hash, str):
                    stored_hash = stored_hash.encode()
                
                salt_bytes = salt
                stored_hash_bytes = stored_hash
            
            # Hash the provided password with the stored salt
            password_hash = hashlib.pbkdf2_hmac('sha256', current_password.encode(), salt_bytes, 100000)
            provided_hash = base64.b64encode(password_hash).decode()
            
            # Compare hashes (convert stored_hash_bytes to base64 for comparison)
            stored_hash_b64 = base64.b64encode(stored_hash_bytes).decode()
            
            if provided_hash == stored_hash_b64:
                return True, "Password verified"
            else:
                return False, "Incorrect password"
                
        except Exception as e:
            self.logger.log_error(f"Error verifying password: {str(e)}")
            return False, f"Error verifying password: {str(e)}"
    
    def change_password(self, username, current_password, new_password):
        """Change user password with current password verification"""
        try:
            # First verify the current password
            is_valid, message = self.verify_current_password(username, current_password)
            if not is_valid:
                return False, message
            
            # Validate new password
            if len(new_password) < 8:
                return False, "New password must be at least 8 characters long"
            
            # Generate new salt and hash
            new_salt_bytes = os.urandom(16)
            new_salt = base64.b64encode(new_salt_bytes).decode()
            new_password_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode(), new_salt_bytes, 100000)
            new_hash = base64.b64encode(new_password_hash).decode()
            
            # Update the password in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", 
                         (new_hash, new_salt, username))
            conn.commit()
            conn.close()
            
            self.logger.log_info(f"Password changed for user: {username}")
            return True, "Password changed successfully"
            
        except Exception as e:
            self.logger.log_error(f"Error changing password: {str(e)}")
            return False, f"Error changing password: {str(e)}"
    
    def update_user_profile(self, username, email=None, mobile_number=None, user_data=None):
        """Update user profile information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query dynamically
            update_fields = []
            update_values = []
            
            if email is not None:
                update_fields.append("email = ?")
                update_values.append(email)
            
            if mobile_number is not None:
                # Validate mobile number if provided
                if mobile_number:
                    is_valid, error_msg = self.validate_mobile_number(mobile_number)
                    if not is_valid:
                        conn.close()
                        return False, error_msg
                update_fields.append("mobile_number = ?")
                update_values.append(mobile_number)
            
            if user_data is not None:
                update_fields.append("user_data = ?")
                update_values.append(json.dumps(user_data))
            
            if not update_fields:
                conn.close()
                return False, "No fields to update"
            
            # Add username to values
            update_values.append(username)
            
            # Execute update
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE username = ?"
            cursor.execute(query, update_values)
            conn.commit()
            conn.close()
            
            # Update current user if it's the same user
            if self.current_user and self.current_user['username'] == username:
                if email is not None:
                    self.current_user['email'] = email
                if mobile_number is not None:
                    self.current_user['mobile_number'] = mobile_number
                if user_data is not None:
                    self.current_user['user_data'] = user_data
            
            self.logger.log_info(f"Profile updated for user: {username}")
            return True, "Profile updated successfully"
            
        except Exception as e:
            self.logger.log_error(f"Error updating profile: {str(e)}")
            return False, f"Error updating profile: {str(e)}"
    
    def get_user_profile(self, username):
        """Get user profile information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, email, mobile_number, user_data, created_at, last_login
                FROM users WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
            
            username, email, mobile_number, user_data, created_at, last_login = result
            
            # Parse user_data JSON
            try:
                user_data_dict = json.loads(user_data) if user_data else {}
            except:
                user_data_dict = {}
            
            profile = {
                'username': username,
                'email': email,
                'mobile_number': mobile_number,
                'user_data': user_data_dict,
                'created_at': created_at,
                'last_login': last_login
            }
            
            return profile
            
        except Exception as e:
            self.logger.log_error(f"Error getting user profile: {str(e)}")
            return None

    def get_encryption_salt(self, username):
        """Get encryption salt for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT encryption_salt FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            else:
                return None
                
        except Exception as e:
            self.logger.log_error(f"Error getting encryption salt: {str(e)}")
            return None

    def ensure_encryption_salt(self, username):
        """Ensure user has encryption salt, generate if missing"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if user has encryption salt
            cursor.execute("SELECT encryption_salt FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            
            if result and result[0]:
                # User already has encryption salt
                conn.close()
                return result[0]
            
            # Generate new encryption salt
            encryption_salt_bytes = os.urandom(16)
            encryption_salt = base64.b64encode(encryption_salt_bytes).decode()
            
            # Update user record
            cursor.execute("UPDATE users SET encryption_salt = ? WHERE username = ?", (encryption_salt, username))
            conn.commit()
            conn.close()
            
            self.logger.log_info(f"Generated encryption salt for user: {username}")
            return encryption_salt
            
        except Exception as e:
            self.logger.log_error(f"Error ensuring encryption salt: {str(e)}")
            return None
