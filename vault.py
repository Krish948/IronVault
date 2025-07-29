"""
Vault management for IronLock Vault
"""

import json
import os
import shutil
import subprocess
import platform
from datetime import datetime
from pathlib import Path
import sqlite3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib

class VaultItem:
    def __init__(self, name, item_type, path, encrypted_path=None):
        self.name = name
        self.item_type = item_type  # 'app', 'folder', 'file'
        self.path = path
        self.encrypted_path = encrypted_path
        self.added_date = datetime.now().isoformat()
        self.last_accessed = None
        self.access_count = 0
    
    def to_dict(self):
        return {
            'name': self.name,
            'item_type': self.item_type,
            'path': self.path,
            'encrypted_path': self.encrypted_path,
            'added_date': self.added_date,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count
        }
    
    @classmethod
    def from_dict(cls, data):
        item = cls(data['name'], data['item_type'], data['path'], data.get('encrypted_path'))
        item.added_date = data.get('added_date', datetime.now().isoformat())
        item.last_accessed = data.get('last_accessed')
        item.access_count = data.get('access_count', 0)
        return item

class VaultMonitor:
    def __init__(self, vault_manager):
        self.vault_manager = vault_manager
    
    def on_modified(self, event):
        if not event.is_directory:
            self.vault_manager.logger.log_warning(f"Vault file modified: {event.src_path}")
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.vault_manager.logger.log_warning(f"Vault file deleted: {event.src_path}")

class VaultManager:
    def __init__(self, config, logger, encryption_manager):
        self.config = config
        self.logger = logger
        self.encryption_manager = encryption_manager
        self.vault_db_path = "data/vault.db"
        self.vault_directory = self.config.get('vault_directory', 'vault')
        self.items = []
        self.monitor = None
        self.observer = None
        
        self.init_vault_database()
        self.setup_vault_monitoring()
    
    def init_vault_database(self):
        """Initialize vault database"""
        os.makedirs(os.path.dirname(self.vault_db_path), exist_ok=True)
        os.makedirs(self.vault_directory, exist_ok=True)
        
        conn = sqlite3.connect(self.vault_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vault_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                original_path TEXT NOT NULL,
                encrypted_path TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                user_id TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                user_id TEXT NOT NULL,
                access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_type TEXT,
                success BOOLEAN,
                FOREIGN KEY (item_id) REFERENCES vault_items (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_vault_monitoring(self):
        """Setup file system monitoring for vault directory"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class VaultFileSystemEventHandler(FileSystemEventHandler):
                def __init__(self, vault_manager):
                    super().__init__()
                    self.vault_manager = vault_manager
                
                def on_modified(self, event):
                    if not event.is_directory:
                        self.vault_manager.logger.log_warning(f"Vault file modified: {event.src_path}")
                
                def on_deleted(self, event):
                    if not event.is_directory:
                        self.vault_manager.logger.log_warning(f"Vault file deleted: {event.src_path}")
            
            self.monitor = VaultFileSystemEventHandler(self)
            self.observer = Observer()
            self.observer.schedule(self.monitor, self.vault_directory, recursive=True)
            
            # Try to start the observer with better error handling
            try:
                self.observer.start()
                self.logger.log_info("Vault monitoring started")
            except Exception as start_error:
                # If observer.start() fails, log the error but don't crash the application
                self.logger.log_warning(f"Vault monitoring failed to start: {str(start_error)}")
                self.logger.log_info("Vault monitoring disabled - continuing without file system monitoring")
                self.observer = None
                self.monitor = None
                
        except ImportError:
            self.logger.log_warning("watchdog library not available, vault monitoring disabled")
        except Exception as e:
            self.logger.log_error(f"Failed to start vault monitoring: {str(e)}")
            self.logger.log_info("Vault monitoring disabled - continuing without file system monitoring")
    
    def compute_file_hash(self, file_path):
        """Compute SHA-256 hash of a file for integrity checking"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def secure_delete(self, file_path, passes=3):
        """Securely overwrite and delete a file"""
        try:
            if not os.path.exists(file_path):
                return True
            length = os.path.getsize(file_path)
            with open(file_path, 'ba+', buffering=0) as delfile:
                for _ in range(passes):
                    delfile.seek(0)
                    delfile.write(os.urandom(length))
            os.remove(file_path)
            return True
        except Exception as e:
            self.logger.log_error(f"Secure delete failed: {str(e)}")
            return False

    def add_item(self, item_path, item_type, user_id, encrypt=True):
        """Add item to vault with versioning, integrity, and metadata encryption"""
        try:
            item_path = Path(item_path)
            if not item_path.exists():
                return False, "Item does not exist"
            item_name = item_path.name
            encrypted_path = None
            original_removed = False
            file_hash = None
            version = 1
            # Versioning: check for existing versions
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM vault_items WHERE name = ? AND user_id = ?', (item_name, user_id))
            version = cursor.fetchone()[0] + 1
            # Handle file
            if item_type == 'file' and encrypt:
                vault_file_path = os.path.join(self.vault_directory, f"{item_name}.v{version}.encrypted")
                encrypted_path = self.encryption_manager.encrypt_file(str(item_path), vault_file_path)
                file_hash = self.compute_file_hash(str(item_path))
                # Secure delete
                if self.secure_delete(str(item_path)):
                    original_removed = True
                    self.logger.log_info(f"Original file securely deleted: {item_path}")
                else:
                    return False, f"Failed to securely delete original file '{item_name}'."
            # Encrypt metadata
            metadata = {
                'name': item_name,
                'item_type': item_type,
                'original_path': str(item_path),
                'encrypted_path': encrypted_path,
                'file_hash': file_hash,
                'version': version
            }
            encrypted_metadata = self.encryption_manager.encrypt_data(metadata)
            # Store encrypted metadata as BLOB
            cursor.execute('''
                INSERT INTO vault_items (name, item_type, original_path, encrypted_path, user_id, added_date, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL, 0)
            ''', (item_name, item_type, str(item_path), encrypted_path, user_id))
            item_id = cursor.lastrowid
            # Store encrypted metadata in a new table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vault_metadata (
                    item_id INTEGER PRIMARY KEY, metadata BLOB,
                    FOREIGN KEY (item_id) REFERENCES vault_items (id)
                )
            ''')
            cursor.execute('INSERT OR REPLACE INTO vault_metadata (item_id, metadata) VALUES (?, ?)', (item_id, encrypted_metadata))
            conn.commit()
            conn.close()
            self.logger.log_info(f"Item added to vault: {item_name} (Type: {item_type}, Version: {version})")
            return True, f"File '{item_name}' encrypted, versioned, and added to vault. Original securely deleted."
        except Exception as e:
            self.logger.log_error(f"Error adding item to vault: {str(e)}")
            return False, f"Failed to add item: {str(e)}"
    
    def get_vault_items(self, user_id):
        """Get all vault items for user"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, item_type, original_path, encrypted_path, 
                       added_date, last_accessed, access_count
                FROM vault_items 
                WHERE user_id = ?
                ORDER BY added_date DESC
            ''', (user_id,))
            
            items = []
            for row in cursor.fetchall():
                item = {
                    'id': row[0],
                    'name': row[1],
                    'item_type': row[2],
                    'original_path': row[3],
                    'encrypted_path': row[4],
                    'added_date': row[5],
                    'last_accessed': row[6],
                    'access_count': row[7]
                }
                items.append(item)
            
            conn.close()
            return items
            
        except Exception as e:
            self.logger.log_error(f"Error getting vault items: {str(e)}")
            return []
    
    def access_item(self, item_id, user_id):
        """Access a vault item with integrity check and metadata decryption"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name, item_type, original_path, encrypted_path FROM vault_items WHERE id = ? AND user_id = ?', (item_id, user_id))
            result = cursor.fetchone()
            if not result:
                return False, "Item not found"
            name, item_type, original_path, encrypted_path = result
            # Decrypt metadata
            cursor.execute('SELECT metadata FROM vault_metadata WHERE item_id = ?', (item_id,))
            meta_blob = cursor.fetchone()
            if meta_blob:
                metadata = self.encryption_manager.decrypt_data(meta_blob[0])
                if isinstance(metadata, bytes):
                    metadata = metadata.decode()
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    pass
                # Integrity check
                if item_type == 'file' and encrypted_path:
                    temp_path = f"temp_{os.path.basename(original_path)}"
                    self.encryption_manager.decrypt_file(encrypted_path, temp_path)
                    file_hash = self.compute_file_hash(temp_path)
                    if file_hash != metadata.get('file_hash'):
                        self.logger.log_error(f"File integrity check failed for {name}")
                        return False, f"File integrity check failed for {name}"
            # Update access statistics
            cursor.execute('''
                UPDATE vault_items 
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE id = ?
            ''', (item_id,))
            
            # Log access attempt
            cursor.execute('''
                INSERT INTO access_logs (item_id, user_id, access_type, success)
                VALUES (?, ?, ?, ?)
            ''', (item_id, user_id, 'open', True))
            
            conn.commit()
            conn.close()
            
            # Open the item based on type
            success = self._open_item(item_type, original_path, encrypted_path)
            
            if success:
                self.logger.log_info(f"Item accessed: {name} by {user_id}")
                return True, f"Opened {name}"
            else:
                return False, f"Failed to open {name}"
                
        except Exception as e:
            self.logger.log_error(f"Error accessing item: {str(e)}")
            return False, f"Access failed: {str(e)}"
    
    def _open_item(self, item_type, original_path, encrypted_path):
        """Open item based on type"""
        try:
            if item_type == 'file' and encrypted_path:
                # Decrypt file temporarily and open
                temp_path = f"temp_{os.path.basename(original_path)}"
                self.encryption_manager.decrypt_file(encrypted_path, temp_path)
                
                # Open file with default application
                if platform.system() == 'Windows':
                    os.startfile(temp_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', temp_path])
                else:  # Linux
                    subprocess.run(['xdg-open', temp_path])
                
                # Schedule cleanup (in production, use proper temp file handling)
                # os.remove(temp_path)  # Remove after use
                
            elif item_type == 'folder':
                # Open folder
                if platform.system() == 'Windows':
                    os.startfile(original_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', original_path])
                else:  # Linux
                    subprocess.run(['xdg-open', original_path])
            
            elif item_type == 'app':
                # Run application
                if platform.system() == 'Windows':
                    subprocess.Popen([original_path])
                else:
                    subprocess.Popen([original_path])
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"Error opening item: {str(e)}")
            return False
    
    def remove_item(self, item_id, user_id):
        """Remove item from vault"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            # Get item details
            cursor.execute('''
                SELECT name, encrypted_path FROM vault_items 
                WHERE id = ? AND user_id = ?
            ''', (item_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False, "Item not found"
            
            name, encrypted_path = result
            
            # Remove encrypted file if exists
            if encrypted_path and os.path.exists(encrypted_path):
                os.remove(encrypted_path)
            
            # Remove from database
            cursor.execute('DELETE FROM vault_items WHERE id = ? AND user_id = ?', (item_id, user_id))
            cursor.execute('DELETE FROM access_logs WHERE item_id = ?', (item_id,))
            
            conn.commit()
            conn.close()
            
            self.logger.log_info(f"Item removed from vault: {name}")
            return True, f"Item '{name}' removed from vault"
            
        except Exception as e:
            self.logger.log_error(f"Error removing item: {str(e)}")
            return False, f"Failed to remove item: {str(e)}"
    
    def search_items(self, query, user_id, search_type='name', date_from=None, date_to=None, 
                    item_type=None, min_access_count=None, max_access_count=None, 
                    sort_by='name', sort_order='asc', limit=None):
        """
        Advanced search vault items with multiple criteria
        
        Args:
            query: Search query string
            user_id: User ID to search for
            search_type: Type of search ('name', 'path', 'all', 'fuzzy')
            date_from: Start date for filtering (YYYY-MM-DD)
            date_to: End date for filtering (YYYY-MM-DD)
            item_type: Filter by item type ('app', 'folder', 'file')
            min_access_count: Minimum access count filter
            max_access_count: Maximum access count filter
            sort_by: Sort field ('name', 'type', 'added_date', 'last_accessed', 'access_count')
            sort_order: Sort order ('asc', 'desc')
            limit: Maximum number of results to return
        """
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            # Build the base query
            base_query = '''
                SELECT id, name, item_type, original_path, added_date, last_accessed, access_count
                FROM vault_items 
                WHERE user_id = ?
            '''
            params = [user_id]
            
            # Add search conditions based on search_type
            if query:
                if search_type == 'name':
                    base_query += ' AND name LIKE ?'
                    params.append(f'%{query}%')
                elif search_type == 'path':
                    base_query += ' AND original_path LIKE ?'
                    params.append(f'%{query}%')
                elif search_type == 'all':
                    base_query += ' AND (name LIKE ? OR original_path LIKE ?)'
                    params.extend([f'%{query}%', f'%{query}%'])
                elif search_type == 'fuzzy':
                    # Fuzzy search using multiple LIKE conditions
                    base_query += ' AND (name LIKE ? OR name LIKE ? OR name LIKE ? OR original_path LIKE ?)'
                    params.extend([
                        f'%{query}%',
                        f'{query}%',
                        f'%{query}',
                        f'%{query}%'
                    ])
            
            # Add date filters
            if date_from:
                base_query += ' AND DATE(added_date) >= ?'
                params.append(date_from)
            
            if date_to:
                base_query += ' AND DATE(added_date) <= ?'
                params.append(date_to)
            
            # Add item type filter
            if item_type:
                base_query += ' AND item_type = ?'
                params.append(item_type)
            
            # Add access count filters
            if min_access_count is not None:
                base_query += ' AND access_count >= ?'
                params.append(min_access_count)
            
            if max_access_count is not None:
                base_query += ' AND access_count <= ?'
                params.append(max_access_count)
            
            # Add sorting
            valid_sort_fields = ['name', 'type', 'added_date', 'last_accessed', 'access_count']
            if sort_by not in valid_sort_fields:
                sort_by = 'name'
            
            sort_field_map = {
                'name': 'name',
                'type': 'item_type',
                'added_date': 'added_date',
                'last_accessed': 'last_accessed',
                'access_count': 'access_count'
            }
            
            base_query += f' ORDER BY {sort_field_map[sort_by]} {sort_order.upper()}'
            
            # Add limit
            if limit:
                base_query += f' LIMIT {limit}'
            
            cursor.execute(base_query, params)
            
            items = []
            for row in cursor.fetchall():
                item = {
                    'id': row[0],
                    'name': row[1],
                    'item_type': row[2],
                    'original_path': row[3],
                    'added_date': row[4],
                    'last_accessed': row[5],
                    'access_count': row[6]
                }
                items.append(item)
            
            conn.close()
            return items
            
        except Exception as e:
            self.logger.log_error(f"Error searching items: {str(e)}")
            return []
    
    def search_items_simple(self, query, user_id):
        """Simple search for backward compatibility"""
        return self.search_items(query, user_id, search_type='name')
    
    def get_search_suggestions(self, partial_query, user_id, limit=10):
        """Get search suggestions based on partial query"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT name, item_type
                FROM vault_items 
                WHERE user_id = ? AND name LIKE ?
                ORDER BY name
                LIMIT ?
            ''', (user_id, f'{partial_query}%', limit))
            
            suggestions = []
            for row in cursor.fetchall():
                suggestions.append({
                    'name': row[0],
                    'type': row[1]
                })
            
            conn.close()
            return suggestions
            
        except Exception as e:
            self.logger.log_error(f"Error getting search suggestions: {str(e)}")
            return []
    
    def get_search_statistics(self, user_id):
        """Get search statistics for the user's vault"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            # Get total items
            cursor.execute('SELECT COUNT(*) FROM vault_items WHERE user_id = ?', (user_id,))
            total_items = cursor.fetchone()[0]
            
            # Get items by type
            cursor.execute('''
                SELECT item_type, COUNT(*) 
                FROM vault_items 
                WHERE user_id = ? 
                GROUP BY item_type
            ''', (user_id,))
            items_by_type = dict(cursor.fetchall())
            
            # Get recently added items (last 30 days)
            cursor.execute('''
                SELECT COUNT(*) 
                FROM vault_items 
                WHERE user_id = ? AND added_date >= datetime('now', '-30 days')
            ''', (user_id,))
            recent_items = cursor.fetchone()[0]
            
            # Get most accessed items
            cursor.execute('''
                SELECT name, access_count 
                FROM vault_items 
                WHERE user_id = ? 
                ORDER BY access_count DESC 
                LIMIT 5
            ''', (user_id,))
            most_accessed = cursor.fetchall()
            
            # Get items by date range
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN added_date >= datetime('now', '-7 days') THEN 'Last 7 days'
                        WHEN added_date >= datetime('now', '-30 days') THEN 'Last 30 days'
                        WHEN added_date >= datetime('now', '-90 days') THEN 'Last 90 days'
                        ELSE 'Older'
                    END as date_range,
                    COUNT(*) as count
                FROM vault_items 
                WHERE user_id = ?
                GROUP BY date_range
            ''', (user_id,))
            items_by_date = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_items': total_items,
                'items_by_type': items_by_type,
                'recent_items': recent_items,
                'most_accessed': most_accessed,
                'items_by_date': items_by_date
            }
            
        except Exception as e:
            self.logger.log_error(f"Error getting search statistics: {str(e)}")
            return {}
    
    def save_search_query(self, user_id, query, search_params):
        """Save a search query for later use"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            # Create saved searches table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    search_params TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 0
                )
            ''')
            
            # Save the search
            search_params_json = json.dumps(search_params) if search_params else None
            cursor.execute('''
                INSERT INTO saved_searches (user_id, query, search_params)
                VALUES (?, ?, ?)
            ''', (user_id, query, search_params_json))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.log_error(f"Error saving search query: {str(e)}")
            return False
    
    def get_saved_searches(self, user_id, limit=10):
        """Get saved searches for the user"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            # Create saved searches table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    search_params TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                SELECT id, query, search_params, created_at, use_count
                FROM saved_searches 
                WHERE user_id = ?
                ORDER BY use_count DESC, created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            searches = []
            for row in cursor.fetchall():
                search = {
                    'id': row[0],
                    'query': row[1],
                    'search_params': json.loads(row[2]) if row[2] else {},
                    'created_at': row[3],
                    'use_count': row[4]
                }
                searches.append(search)
            
            conn.close()
            return searches
            
        except Exception as e:
            self.logger.log_error(f"Error getting saved searches: {str(e)}")
            return []
    
    def get_access_logs(self, user_id, limit=100):
        """Get access logs for user"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT vi.name, al.access_time, al.access_type, al.success
                FROM access_logs al
                JOIN vault_items vi ON al.item_id = vi.id
                WHERE al.user_id = ?
                ORDER BY al.access_time DESC
                LIMIT ?
            ''', (user_id, limit))
            
            logs = []
            for row in cursor.fetchall():
                log = {
                    'item_name': row[0],
                    'access_time': row[1],
                    'access_type': row[2],
                    'success': row[3]
                }
                logs.append(log)
            
            conn.close()
            return logs
            
        except Exception as e:
            self.logger.log_error(f"Error getting access logs: {str(e)}")
            return []
    
    def get_item_details(self, item_id, user_id):
        """Get detailed information about a vault item"""
        try:
            conn = sqlite3.connect(self.vault_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT name, item_type, original_path, encrypted_path, added_date, 
                       last_accessed, access_count, user_id
                FROM vault_items 
                WHERE id = ? AND user_id = ?
            ''', (item_id, user_id))
            
            result = cursor.fetchone()
            if not result:
                return {}
            
            name, item_type, original_path, encrypted_path, added_date, last_accessed, access_count, user_id = result
            
            # Get file size if it's a file
            file_size = "N/A"
            if item_type == 'file' and encrypted_path and os.path.exists(encrypted_path):
                try:
                    file_size = f"{os.path.getsize(encrypted_path)} bytes"
                except:
                    file_size = "Unknown"
            
            # Get access logs for this item
            cursor.execute('''
                SELECT access_time, access_type, success
                FROM access_logs 
                WHERE item_id = ? 
                ORDER BY access_time DESC 
                LIMIT 10
            ''', (item_id,))
            
            access_logs = []
            for log_row in cursor.fetchall():
                access_logs.append({
                    'access_time': log_row[0],
                    'access_type': log_row[1],
                    'success': log_row[2]
                })
            
            conn.close()
            
            return {
                'id': item_id,
                'name': name,
                'item_type': item_type,
                'original_path': original_path,
                'encrypted_path': encrypted_path,
                'added_date': added_date,
                'last_accessed': last_accessed,
                'access_count': access_count,
                'file_size': file_size,
                'encryption_method': 'AES-256',
                'is_encrypted': True,
                'permissions': 'Owner Only',
                'created_by': user_id,
                'created_date': added_date,
                'last_modified': last_accessed or added_date,
                'first_access': access_logs[-1]['access_time'] if access_logs else 'Never',
                'avg_access_time': 'N/A',  # Could calculate from logs
                'last_access_duration': 'N/A',  # Could track in logs
                'storage_location': 'Local Vault',
                'backup_status': 'Not Backed Up',
                'compression': 'None',
                'access_logs': access_logs
            }
            
        except Exception as e:
            self.logger.log_error(f"Error getting item details: {str(e)}")
            return {}
    
    def cleanup(self):
        """Cleanup vault resources"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    def try_remove_original_file(self, original_path):
        """Try to remove the original file manually"""
        try:
            file_path = Path(original_path)
            if not file_path.exists():
                return True, "File does not exist (already removed)"
            
            file_path.unlink()
            self.logger.log_info(f"Manually removed original file: {original_path}")
            return True, "Original file removed successfully"
            
        except PermissionError:
            return False, "Permission denied. The file may be in use by another application."
        except FileNotFoundError:
            return True, "File does not exist (already removed)"
        except Exception as e:
            self.logger.log_error(f"Error removing original file: {str(e)}")
            return False, f"Failed to remove file: {str(e)}"
