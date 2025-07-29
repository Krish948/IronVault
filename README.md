# IronLock Vault - Complete Documentation

A comprehensive desktop vault application with advanced encryption, two-factor authentication, and enhanced search capabilities.

## Table of Contents

1. [Features](#-features)
2. [Installation](#️-installation)
3. [Usage](#-usage)
4. [Configuration](#-configuration)
5. [File Structure](#-file-structure)
6. [Search Enhancement Details](#-search-enhancement-details)
7. [Security Implementation](#-security-implementation)
8. [Performance Optimizations](#-performance-optimizations)
9. [Development](#-development)
10. [Requirements and Dependencies](#requirements-and-dependencies)
11. [Privacy and Data Security](#-privacy-and-data-security)
12. [License and Contributing](#-license-and-contributing)
13. [Known Issues and Future Enhancements](#-known-issues-and-future-enhancements)

---

## 🚀 Features

### 🔐 Security Features
- **AES-256 Encryption**: All vault items are encrypted using industry-standard AES-256 encryption
- **Two-Factor Authentication**: TOTP-based 2FA with QR code setup
- **Auto-Lock**: Automatic vault locking after inactivity
- **Secure File Deletion**: Original files are securely overwritten and deleted
- **Access Logging**: Comprehensive logging of all vault access attempts
- **Integrity Checking**: File integrity verification for encrypted items

### 🔍 Enhanced Search Functionality
- **Advanced Search**: Multiple search criteria including name, path, type, and date ranges
- **Fuzzy Search**: Intelligent search with partial matching and suggestions
- **Real-time Search**: Instant search results as you type
- **Search Filters**: Filter by item type, access count, and date ranges
- **Search Statistics**: Comprehensive vault analytics and usage statistics
- **Saved Searches**: Save and reuse frequently used search queries
- **Search Suggestions**: Auto-complete suggestions based on vault contents

### 📱 User Interface
- **Modern UI**: Clean, intuitive interface with dark theme support
- **Responsive Design**: Adapts to different screen sizes
- **Keyboard Shortcuts**: Quick access to common functions
- **Context Menus**: Right-click actions for items
- **Drag & Drop**: Easy file addition to vault
- **Progress Indicators**: Visual feedback for operations

### 📊 Vault Management
- **Multiple Item Types**: Support for files, folders, and applications
- **Version Control**: Automatic versioning of vault items
- **Bulk Operations**: Select and manage multiple items at once
- **Export Capabilities**: Export search results and vault statistics
- **Backup Support**: Local backup and restore functionality

---

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Windows, macOS, or Linux

### Setup
1. Clone the repository:
```bash
git clone https://github.com/yourusername/ironlock-vault.git
cd ironlock-vault
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application (optional):
   - Run the setup script: `python scripts/setup_new_user.py`
   - Or manually copy `data/config.sample.json` to `data/config.json`
   - Edit `data/config.json` with your personal settings
   - Configure email/SMS settings if you want to use 2FA

4. Run the application:
```bash
python main.py
```

---

## 📖 Usage

### First-Time Setup
1. Launch the application
2. Create a new account with strong password
3. Set up two-factor authentication (recommended)
4. Configure security preferences
5. Start adding items to your vault

### Adding Items to Vault
- **Files**: Drag and drop or use "Add File" button
- **Folders**: Select folder to add entire directory structure
- **Applications**: Add executable files for quick access

### Advanced Search Features

#### Quick Search
- Type in the search bar for instant results
- Results update in real-time as you type
- Supports fuzzy matching for better results

#### Advanced Search Dialog
- **Search Types**: Name, path, all fields, or fuzzy search
- **Date Filters**: Filter by date ranges (added date)
- **Type Filters**: Filter by item type (app, folder, file)
- **Access Count**: Filter by minimum/maximum access count
- **Sorting**: Sort by name, type, date, access count
- **Saved Searches**: Save frequently used search queries

#### Search Statistics
- Total item count and recent additions
- Items by type breakdown
- Most accessed items
- Date range distribution
- Usage analytics

### Security Features

#### Two-Factor Authentication
- QR code setup for authenticator apps
- Email and SMS OTP options
- Backup codes for account recovery
- TOTP secret management

#### Auto-Lock
- Configurable inactivity timeout
- Global hotkey for quick lock (Ctrl+Shift+L)
- Activity monitoring
- Secure session management

---

## 🔧 Configuration

### Application Settings
- **Theme**: Choose from multiple ttkbootstrap themes
- **Auto-lock Timeout**: Set inactivity timeout (minutes)
- **2FA Requirements**: Configure 2FA for sensitive actions
- **Window Size**: Customize application window dimensions

### Security Settings
- **Encryption**: AES-256 encryption for all vault items
- **File Integrity**: SHA-256 hash verification
- **Secure Deletion**: Multi-pass file overwriting
- **Access Logging**: Comprehensive audit trail

---

## 📁 File Structure

```
IronLock Vault/
├── main.py              # Application entry point
├── ui.py                # User interface components
├── vault.py             # Vault management and search
├── auth.py              # Authentication and 2FA
├── encryption.py        # Encryption utilities
├── config.py            # Configuration management
├── logger.py            # Logging system
├── data/                # Application data
│   ├── config.json      # Configuration file
│   ├── users.db         # User database
│   └── vault.db         # Vault items database
├── logs/                # Application logs
│   ├── security.log     # Security events
│   └── vault.log        # General application logs
├── vault/               # Encrypted vault storage
└── scripts/             # Utility scripts
    ├── setup_database.py
    ├── configure_otp.py
    └── create_test_user.py
```

---

## 🔍 Search Enhancement Details

### Enhanced Search Methods

#### 1. Basic Search (`search_items_simple`)
- Simple name-based search
- Backward compatibility
- Fast performance

#### 2. Advanced Search (`search_items`)
- **Multiple search types**:
  - `name`: Search in item names only
  - `path`: Search in original file paths
  - `all`: Search in both names and paths
  - `fuzzy`: Intelligent partial matching
- **Date filtering**: Filter by added date ranges
- **Type filtering**: Filter by item type (app, folder, file)
- **Access count filtering**: Filter by minimum/maximum access count
- **Sorting options**: Sort by name, type, date, access count
- **Result limiting**: Limit number of results for performance

#### 3. Search Suggestions (`get_search_suggestions`)
- Auto-complete suggestions
- Based on partial queries
- Configurable suggestion limit

#### 4. Search Statistics (`get_search_statistics`)
- Total item count
- Items by type breakdown
- Recent additions (last 30 days)
- Most accessed items
- Date range distribution

#### 5. Saved Searches
- Save frequently used search queries
- Track search usage count
- Quick access to saved searches

### Search UI Enhancements

#### 1. Real-time Search
- Instant results as you type
- Fuzzy matching for better results
- Status updates with result counts

#### 2. Advanced Search Dialog
- **Modern interface** with scrollable content
- **Multiple search criteria** in organized sections
- **Collapsible advanced filters**
- **Enhanced results display** with more columns
- **Export functionality** for search results
- **Statistics view** with comprehensive analytics

#### 3. Search Results
- **Enhanced treeview** with more information
- **Path truncation** for better display
- **Type icons** for visual identification
- **Double-click access** with 2FA verification
- **Context menus** for additional actions

#### 4. Saved Searches Panel
- **List of saved searches** with usage counts
- **Quick access** to previous searches
- **Search history** management

---

## 🔐 Security Implementation

### Encryption
- **AES-256** encryption for all vault items
- **Unique encryption keys** per user
- **Salt-based key derivation** for password security
- **Secure key storage** in user database

### Two-Factor Authentication
- **TOTP implementation** compatible with Google Authenticator
- **QR code generation** for easy setup
- **Email/SMS OTP** as backup options
- **Backup codes** for account recovery

### File Security
- **Secure deletion** with multiple overwrite passes
- **Integrity checking** using SHA-256 hashes
- **Access logging** for audit trails
- **Permission-based access** control

---

## 🚀 Performance Optimizations

### Search Performance
- **Indexed database queries** for fast searches
- **Result limiting** to prevent memory issues
- **Cached search results** for repeated queries
- **Asynchronous search** for large vaults

### UI Performance
- **Lazy loading** of search results
- **Virtual scrolling** for large item lists
- **Background processing** for heavy operations
- **Memory-efficient** treeview implementation

---

## 🔧 Development

### Adding New Search Features
1. Extend the `search_items` method in `vault.py`
2. Add UI components in `ui.py`
3. Update documentation in `README.md`
4. Test with various data types

### Customizing Search UI
- Modify the search dialog in `ui.py`
- Add new filter options
- Enhance result display
- Implement additional export formats

---

## Requirements and Dependencies

This section covers dependency management files for the IronLock Vault application.

### Files Overview

#### `requirements.txt`
Main requirements file containing all external dependencies needed to run the application.

**Installation:**
```bash
pip install -r requirements/requirements.txt
```

#### `requirements-dev.txt`
Development requirements including testing frameworks, code quality tools, and documentation generators.

**Installation:**
```bash
pip install -r requirements/requirements-dev.txt
```

#### `requirements-prod.txt`
Minimal production requirements with only essential dependencies for deployment.

**Installation:**
```bash
pip install -r requirements/requirements-prod.txt
```

### Dependencies Breakdown

#### Core Dependencies
- **ttkbootstrap**: Modern GUI framework for enhanced UI components
- **Pillow**: Image processing for file previews and icons
- **cryptography**: Encryption and security functions
- **pyotp**: Two-factor authentication implementation
- **watchdog**: File system monitoring for vault changes

#### Development Dependencies
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Code linting
- **mypy**: Type checking
- **sphinx**: Documentation generation
- **bandit**: Security vulnerability scanning

### Installation Instructions

#### For Development
```bash
# Install all dependencies including development tools
pip install -r requirements/requirements-dev.txt
```

#### For Production
```bash
# Install only production dependencies
pip install -r requirements/requirements-prod.txt
```

#### For Basic Usage
```bash
# Install core dependencies only
pip install -r requirements/requirements.txt
```

### Version Management

All dependencies specify minimum versions to ensure compatibility while allowing for security updates. The application has been tested with the specified minimum versions.

### Security Notes

- All cryptographic dependencies are from well-maintained libraries
- Regular security updates are recommended
- Use `safety` tool to check for known vulnerabilities: `safety check -r requirements/requirements.txt`

---

## 🔒 Privacy and Data Security

IronLock Vault is designed with privacy and security as top priorities. This section explains how your personal data is handled and protected.

### Personal Data Protection

#### What Data is Stored Locally

**User Data:**
- User accounts and encrypted passwords (stored in `data/users.db`)
- Vault item metadata (stored in `data/vault.db`)
- Encrypted vault contents (stored in `vault/` directory)
- Application logs (stored in `logs/` directory)
- Personal configuration settings (stored in `data/config.json`)

**What is NOT included in the repository:**
- ❌ User databases (`data/users.db`, `data/vault.db`)
- ❌ Personal configuration (`data/config.json`)
- ❌ Application logs (`logs/` directory)
- ❌ Encrypted vault contents (`vault/` directory)
- ❌ Personal phone numbers, email addresses, or other identifiers

### Data Encryption

**All sensitive data is encrypted:**
- Vault contents: AES-256 encryption
- User passwords: Salted hash with bcrypt
- Configuration: Plain text (contains no sensitive data by default)

### Privacy Features

**Local Storage Only:**
- All data remains on your local machine
- No cloud storage or external servers
- No data collection or analytics

**Configurable Logging:**
- Logs can be disabled entirely
- Log retention can be configured
- No personal information in logs by default

**Secure Deletion:**
- Original files are securely overwritten before deletion
- Multiple pass overwriting for sensitive data
- No traces left on disk

### Setup for New Users

1. **Fresh Installation:**
   - No personal data in the repository
   - Clean slate for new users
   - Sample configuration provided

2. **Configuration:**
   - Copy `data/config.sample.json` to `data/config.json`
   - Add your personal settings (email, phone, etc.)
   - Configuration file is excluded from git

3. **Data Creation:**
   - User databases created on first use
   - Log files created as needed
   - Vault directory created automatically

### Git Ignore Protection

The `.gitignore` file ensures sensitive files are never accidentally committed:

```
# Personal and sensitive data
data/users.db
data/vault.db
data/config.json
logs/
vault/
*.encrypted
```

### Best Practices

**For Users:**
- Keep your configuration file secure
- Regularly backup your vault data
- Use strong passwords and 2FA
- Review log files periodically

**For Developers:**
- Never commit personal data
- Use the sample configuration as template
- Test with dummy data only
- Follow the privacy guidelines

### Compliance

- **GDPR Compliant**: Local storage only, no external data processing
- **No Tracking**: No analytics or user tracking
- **Transparent**: Open source code for full transparency
- **User Control**: Complete control over personal data

### Support

If you have privacy concerns or questions:
1. Review the source code for transparency
2. Check the configuration files for data handling
3. Contact the project maintainers for clarification

**Remember**: Your privacy is important. This application is designed to keep your data secure and local to your machine.

---

## 📝 License and Contributing

This project is licensed under the MIT License - see the LICENSE file for details.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 🐛 Known Issues and Future Enhancements

### Known Issues

- Large vaults may experience slower search performance
- Some file types may not display properly in results
- Export functionality is limited to basic formats

### Future Enhancements

- **Cloud backup** integration
- **Advanced analytics** and reporting
- **Plugin system** for custom search filters
- **Mobile companion** app
- **Web interface** for remote access
- **Advanced export** formats (CSV, JSON, XML)
- **Search result highlighting** and preview
- **Batch operations** on search results
#   I r o n V a u l t 
 
 
