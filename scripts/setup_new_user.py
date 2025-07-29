#!/usr/bin/env python3
"""
Setup script for new IronLock Vault users
Helps configure the application with personal settings
"""

import os
import shutil
import json
from pathlib import Path

def setup_new_user():
    """Setup the application for a new user"""
    print("🔐 IronLock Vault - New User Setup")
    print("=" * 50)
    
    # Create necessary directories
    directories = ["data", "logs", "vault"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}/")
    
    # Setup configuration file
    config_file = "data/config.json"
    sample_config = "data/config.sample.json"
    
    if not os.path.exists(config_file):
        if os.path.exists(sample_config):
            shutil.copy(sample_config, config_file)
            print(f"✅ Created configuration file: {config_file}")
            print("   Edit this file to customize your settings")
        else:
            print("⚠️  Sample configuration file not found")
    else:
        print(f"✅ Configuration file already exists: {config_file}")
    
    # Create .gitignore if it doesn't exist
    gitignore_file = ".gitignore"
    if not os.path.exists(gitignore_file):
        print("⚠️  .gitignore file not found - creating one")
        gitignore_content = """# Personal and sensitive data
data/users.db
data/vault.db
data/config.json
logs/
vault/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporary files
*.tmp
*.temp
*.log

# Backup files
*.bak
*.backup

# Environment variables
.env
.env.local
.env.production

# Database files (in case they contain sensitive data)
*.db
*.sqlite
*.sqlite3

# Encrypted files
*.encrypted
"""
        with open(gitignore_file, 'w') as f:
            f.write(gitignore_content)
        print(f"✅ Created .gitignore file")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit data/config.json with your personal settings")
    print("2. Configure email/SMS settings if you want to use 2FA")
    print("3. Run 'python main.py' to start the application")
    print("\n📝 Note: All personal data will be stored locally and is not tracked by git")

if __name__ == "__main__":
    setup_new_user() 