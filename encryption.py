"""
Encryption and decryption utilities for IronLock Vault
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json

class EncryptionManager:
    def __init__(self, config):
        self.config = config
        self.key = None
        self.fernet = None
    
    def generate_key_from_password(self, password, salt=None):
        """Generate encryption key from password"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def initialize_encryption(self, password, salt=None):
        """Initialize encryption with password"""
        self.key, salt = self.generate_key_from_password(password, salt)
        self.fernet = Fernet(self.key)
        return salt
    
    def encrypt_data(self, data):
        """Encrypt data"""
        if self.fernet is None:
            raise ValueError("Encryption not initialized")
        
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data).encode()
        
        return self.fernet.encrypt(data)
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data"""
        if self.fernet is None:
            raise ValueError("Encryption not initialized")
        
        return self.fernet.decrypt(encrypted_data)
    
    def encrypt_file(self, file_path, output_path=None):
        """Encrypt a file"""
        if self.fernet is None:
            raise ValueError("Encryption not initialized")
        
        if output_path is None:
            output_path = file_path + ".encrypted"
        
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        encrypted_data = self.fernet.encrypt(file_data)
        
        with open(output_path, 'wb') as file:
            file.write(encrypted_data)
        
        return output_path
    
    def decrypt_file(self, encrypted_file_path, output_path=None):
        """Decrypt a file"""
        if self.fernet is None:
            raise ValueError("Encryption not initialized")
        
        with open(encrypted_file_path, 'rb') as file:
            encrypted_data = file.read()
        
        decrypted_data = self.fernet.decrypt(encrypted_data)
        
        if output_path:
            with open(output_path, 'wb') as file:
                file.write(decrypted_data)
            return output_path
        else:
            return decrypted_data
    
    def hash_password(self, password, salt=None):
        """Hash password with salt"""
        if salt is None:
            salt = os.urandom(32)
        
        pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                      password.encode('utf-8'), 
                                      salt, 
                                      100000)
        return pwdhash, salt
    
    def verify_password(self, password, stored_hash, salt):
        """Verify password against stored hash"""
        pwdhash, _ = self.hash_password(password, salt)
        return pwdhash == stored_hash
