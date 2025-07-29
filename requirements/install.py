#!/usr/bin/env python3
"""
IronLock Vault - Dependency Installer
Automated script to install project dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies(requirements_file):
    """Install dependencies from a requirements file"""
    if not os.path.exists(requirements_file):
        print(f"❌ Requirements file not found: {requirements_file}")
        return False
    
    return run_command(
        f"{sys.executable} -m pip install -r {requirements_file}",
        f"Installing dependencies from {requirements_file}"
    )

def main():
    """Main installation function"""
    print("🚀 IronLock Vault - Dependency Installer")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Get script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Determine which requirements to install
    if len(sys.argv) > 1:
        install_type = sys.argv[1].lower()
    else:
        print("\n📋 Available installation options:")
        print("1. Basic (core dependencies only)")
        print("2. Development (includes testing and development tools)")
        print("3. Production (minimal dependencies)")
        
        while True:
            choice = input("\nSelect installation type (1/2/3): ").strip()
            if choice in ['1', '2', '3']:
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        install_type = {
            '1': 'basic',
            '2': 'development', 
            '3': 'production'
        }[choice]
    
    # Install based on type
    if install_type in ['basic', 'dev', 'development']:
        requirements_file = "requirements.txt"
        if install_type in ['dev', 'development']:
            requirements_file = "requirements-dev.txt"
        success = install_dependencies(requirements_file)
    elif install_type in ['prod', 'production']:
        success = install_dependencies("requirements-prod.txt")
    else:
        print(f"❌ Unknown installation type: {install_type}")
        print("Valid options: basic, development, production")
        sys.exit(1)
    
    if success:
        print("\n🎉 Installation completed successfully!")
        print("You can now run the IronLock Vault application.")
    else:
        print("\n❌ Installation failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 