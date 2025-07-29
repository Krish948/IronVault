"""
User Interface for IronLock Vault
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttk_bootstrap
from ttkbootstrap.constants import *
import os
import json
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from pathlib import Path
import csv
from tkinter import simpledialog
import tkinter.font as tkfont
import re

# Try to import QR scanner modules
try:
    from qr_scanner import QRScanner, QRScannerUI
    QR_SCANNER_AVAILABLE = True
except ImportError:
    QR_SCANNER_AVAILABLE = False

try:
    from qr_scanner_web import WebQRScanner, WebQRScannerUI
    WEB_QR_SCANNER_AVAILABLE = True
except ImportError:
    WEB_QR_SCANNER_AVAILABLE = False

# --- Custom Message Dialog with Window Controls ---
class CustomMessageDialog:
    """Custom message dialog with minimize/maximize buttons"""
    
    def __init__(self, parent, title, message, dialog_type="info"):
        self.parent = parent
        self.title = title
        self.message = message
        self.dialog_type = dialog_type
        
        # Create the dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        
        # Center the window
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 200
        y = (self.dialog.winfo_screenheight() // 2) - 100
        self.dialog.geometry(f'400x200+{x}+{y}')
        
        # Main frame
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Icon and title
        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅",
            "question": "❓"
        }
        icon = icon_map.get(dialog_type, "ℹ️")
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(title_frame, text=icon, font=('Arial', 24)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(title_frame, text=title, font=('Arial', 14, 'bold')).pack(side=tk.LEFT)
        
        # Message
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create scrollable text widget for long messages
        text_container = ttk.Frame(message_frame)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        text_widget = tk.Text(text_container, wrap=tk.WORD, font=('Arial', 10), 
                             bg='white', fg='black', height=6, padx=10, pady=10,
                             borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert(tk.END, message)
        text_widget.config(state=tk.DISABLED)
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            self.dialog.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        self.is_maximized = False
        def toggle_maximize():
            if self.is_maximized:
                self.dialog.geometry("400x200")
                self.is_maximized = False
            else:
                self.dialog.state('zoomed')
                self.is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - OK button
        ttk.Button(control_frame, text="OK", command=self.dialog.destroy, 
                  style='primary.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_dialog_close():
            self.dialog.destroy()
        
        self.dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Focus on the dialog
        self.dialog.focus_set()
        self.dialog.grab_set()
    
    def show(self):
        """Show the dialog and wait for it to close"""
        self.dialog.wait_window()
        return True

# --- Tooltip Utility ---
class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<Motion>', self.motion)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def motion(self, event=None):
        self.x = event.x_root + 20
        self.y = event.y_root + 10
        if self.tipwindow:
            self.tipwindow.geometry(f'+{self.x}+{self.y}')

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.showtip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{self.x}+{self.y}')
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background='#ffffe0', relief=tk.SOLID, borderwidth=1,
                         font=('tahoma', '9', 'normal'))
        label.pack(ipadx=6, ipady=2)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class VaultUI:
    def __init__(self, root, auth_manager, vault_manager, config, logger, app_instance=None):
        self.root = root
        self.auth_manager = auth_manager
        self.vault_manager = vault_manager
        self.config = config
        self.logger = logger
        self.app_instance = app_instance  # Reference to main application
        
        self.is_logged_in = False
        self.current_user = None
        
        # --- Splash Screen ---
        self.show_splash_screen()
        
        # Setup main window
        self.setup_main_window()
        
        # Initialize UI
        self.setup_login_ui()
        
        self.selected_items = set()  # Track selected item IDs
        # Create checkbox images
        self.checkbox_unchecked = tk.PhotoImage(width=16, height=16)
        self.checkbox_checked = tk.PhotoImage(width=16, height=16)
        # Draw unchecked box
        self.checkbox_unchecked.put(("#ffffff",), to=(0,0,15,15))
        self.checkbox_unchecked.put(("#000000",), to=(0,0,15,0))
        self.checkbox_unchecked.put(("#000000",), to=(0,0,0,15))
        self.checkbox_unchecked.put(("#000000",), to=(15,0,15,15))
        self.checkbox_unchecked.put(("#000000",), to=(0,15,15,15))
        # Draw checked box
        self.checkbox_checked.put(("#ffffff",), to=(0,0,15,15))
        self.checkbox_checked.put(("#000000",), to=(0,0,15,0))
        self.checkbox_checked.put(("#000000",), to=(0,0,0,15))
        self.checkbox_checked.put(("#000000",), to=(15,0,15,15))
        self.checkbox_checked.put(("#000000",), to=(0,15,15,15))
        # Draw check mark
        for i in range(4, 12):
            self.checkbox_checked.put(("#008000",), to=(i, i, i+1, i+1))
        for i in range(4, 8):
            self.checkbox_checked.put(("#008000",), to=(i, 16-i, i+1, 17-i))
    
    def show_custom_message(self, title, message, dialog_type="info"):
        """Show a custom message dialog with minimize/maximize buttons"""
        dialog = CustomMessageDialog(self.root, title, message, dialog_type)
        return dialog.show()
    
    def show_custom_info(self, title, message):
        """Show custom info message"""
        return self.show_custom_message(title, message, "info")
    
    def show_custom_warning(self, title, message):
        """Show custom warning message"""
        return self.show_custom_message(title, message, "warning")
    
    def show_custom_error(self, title, message):
        """Show custom error message"""
        return self.show_custom_message(title, message, "error")
    
    def show_custom_success(self, title, message):
        """Show custom success message"""
        return self.show_custom_message(title, message, "success")
    
    def create_password_field(self, parent, show_label=True, label_text="Password:", confirm_field=None):
        """
        Create a password field with show/hide functionality
        
        Args:
            parent: Parent widget
            show_label: Whether to show the label
            label_text: Text for the label
            confirm_field: Reference to confirm password field for validation
            
        Returns:
            tuple: (entry_widget, show_button)
        """
        # Create frame to hold entry and button
        field_frame = ttk.Frame(parent)
        
        if show_label:
            ttk.Label(field_frame, text=label_text).pack(anchor=W, pady=(0, 5))
        
        # Create entry and button frame
        entry_button_frame = ttk.Frame(field_frame)
        entry_button_frame.pack(fill=X)
        
        # Password entry
        entry = ttk.Entry(entry_button_frame, show="*", font=('Arial', 12))
        entry.pack(side=LEFT, fill=X, expand=True)
        
        # Show/Hide button
        show_button = ttk.Button(
            entry_button_frame, 
            text="👁", 
            width=3,
            command=lambda: self.toggle_password_visibility(entry, show_button)
        )
        show_button.pack(side=RIGHT, padx=(5, 0))
        
        return entry, show_button, field_frame
    
    def toggle_password_visibility(self, entry, button):
        """Toggle password visibility between hidden and shown"""
        if entry.cget('show') == '*':
            entry.config(show='')
            button.config(text="🙈")
        else:
            entry.config(show='*')
            button.config(text="👁")
    
    def setup_main_window(self):
        """Setup main window properties"""
        self.root.title(self.config.get('app_name', 'IronLock Vault'))
        self.root.geometry(self.config.get('window_size', '1200x800'))
        self.root.resizable(True, True)
        
        # Set theme
        style = ttk_bootstrap.Style(theme=self.config.get('theme', 'darkly'))
        
        # Center window
        self.center_window()
        
        # Set icon (if available)
        try:
            self.root.iconbitmap('assets/icon.ico')
        except:
            pass
    
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_login_ui(self):
        """Setup login interface with improved layout and logo/banner"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        # Logo/banner at top - centered vertically
        logo_frame = ttk.Frame(main_frame)
        logo_frame.pack(pady=(0, 20))
        logo_label = ttk.Label(logo_frame, text="🛡️", font=("Arial", 48))
        logo_label.pack(pady=(0, 10), anchor=tk.E, padx=(0, 20))
        name_label = ttk.Label(logo_frame, text="IronLock Vault", font=("Arial", 24, "bold"))
        name_label.pack(anchor=tk.W, padx=(20, 0))
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🔒 Secure Desktop Vault Login", 
            font=('Arial', 20, 'bold')
        )
        title_label.pack(pady=(10, 30))
        # Login frame
        login_frame = ttk.LabelFrame(main_frame, text="Login", padding=30)
        login_frame.pack(pady=20, padx=50, fill=tk.X)
        # Username
        ttk.Label(login_frame, text="Username:").pack(anchor=tk.W, pady=(0, 5))
        self.username_entry = ttk.Entry(login_frame, font=('Arial', 12))
        self.username_entry.pack(fill=tk.X, pady=(0, 15))
        # Password
        self.password_entry, self.password_show_btn, password_field = self.create_password_field(
            login_frame, 
            show_label=True, 
            label_text="Password:"
        )
        password_field.pack(fill=tk.X, pady=(0, 20))
        # Login button
        login_btn = ttk.Button(
            login_frame, 
            text="Login", 
            command=self.login,
            style='success.TButton'
        )
        login_btn.pack(pady=10)
        # Register button
        register_btn = ttk.Button(
            login_frame, 
            text="Register New User", 
            command=self.show_register_ui,
            style='info.TButton'
        )
        register_btn.pack(pady=5)
        # Bind Enter key
        self.root.bind('<Return>', lambda e: self.login())
        # Focus on username entry
        self.username_entry.focus()
    
    def show_register_ui(self):
        """Show registration interface with enhanced scrolling"""
        register_window = tk.Toplevel(self.root)
        register_window.title("Register New User - IronLock Vault")
        register_window.geometry("500x600")
        register_window.transient(self.root)
        register_window.grab_set()
        register_window.resizable(True, True)
        
        # Center the window
        register_window.update_idletasks()
        x = (register_window.winfo_screenwidth() // 2) - 250
        y = (register_window.winfo_screenheight() // 2) - 300
        register_window.geometry(f'500x600+{x}+{y}')
        
        # Main container with scrollbar
        main_container = ttk.Frame(register_window)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Title
        ttk.Label(main_container, text="👤 Create New Account", 
                 font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Registration form
        form_frame = ttk.LabelFrame(scrollable_frame, text="Account Information", padding=20)
        form_frame.pack(fill=X, pady=(0, 20))
        
        # Username section
        username_frame = ttk.LabelFrame(form_frame, text="Username", padding=10)
        username_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(username_frame, text="Choose a unique username:").pack(anchor=W, pady=(0, 5))
        username_entry = ttk.Entry(username_frame, font=('Arial', 12))
        username_entry.pack(fill=X, pady=(0, 5))
        ttk.Label(username_frame, text="Username must be 3-20 characters, letters and numbers only", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Password section
        password_frame = ttk.LabelFrame(form_frame, text="Password", padding=10)
        password_frame.pack(fill=X, pady=(0, 15))
        
        # Create password field
        password_entry, password_show_btn, password_field = self.create_password_field(
            password_frame, 
            show_label=True, 
            label_text="Create a strong password:"
        )
        password_field.pack(fill=X, pady=(0, 5))
        
        # Create confirm password field
        confirm_password_entry, confirm_show_btn, confirm_field = self.create_password_field(
            password_frame, 
            show_label=True, 
            label_text="Confirm your password:"
        )
        confirm_field.pack(fill=X, pady=(0, 5))
        
        # Password strength indicator
        strength_label = ttk.Label(password_frame, text="Password strength: ", 
                                  font=('Arial', 9), foreground='gray')
        strength_label.pack(anchor=W, pady=(5, 0))
        
        def check_password_strength():
            password = password_entry.get()
            if len(password) == 0:
                strength_label.config(text="Password strength: ", foreground='gray')
                return
            
            score = 0
            feedback = []
            
            if len(password) >= 8:
                score += 1
            else:
                feedback.append("At least 8 characters")
            
            if any(c.isupper() for c in password):
                score += 1
            else:
                feedback.append("Include uppercase letters")
            
            if any(c.islower() for c in password):
                score += 1
            else:
                feedback.append("Include lowercase letters")
            
            if any(c.isdigit() for c in password):
                score += 1
            else:
                feedback.append("Include numbers")
            
            if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                score += 1
            else:
                feedback.append("Include special characters")
            
            if score <= 2:
                strength_label.config(text=f"Password strength: Weak - {'; '.join(feedback)}", foreground='red')
            elif score <= 3:
                strength_label.config(text=f"Password strength: Fair - {'; '.join(feedback)}", foreground='orange')
            elif score <= 4:
                strength_label.config(text=f"Password strength: Good - {'; '.join(feedback)}", foreground='blue')
            else:
                strength_label.config(text="Password strength: Strong ✓", foreground='green')
        
        password_entry.bind('<KeyRelease>', lambda e: check_password_strength())
        
        # Personal Information section
        personal_frame = ttk.LabelFrame(scrollable_frame, text="Personal Information (Optional)", padding=20)
        personal_frame.pack(fill=X, pady=(0, 20))
        
        # Email
        ttk.Label(personal_frame, text="Email Address:").pack(anchor=W, pady=(0, 5))
        email_entry = ttk.Entry(personal_frame, font=('Arial', 12))
        email_entry.pack(fill=X, pady=(0, 15))
        ttk.Label(personal_frame, text="Used for password recovery and 2FA", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Mobile Number
        ttk.Label(personal_frame, text="Mobile Number:").pack(anchor=W, pady=(0, 5))
        mobile_entry = ttk.Entry(personal_frame, font=('Arial', 12))
        mobile_entry.pack(fill=X, pady=(0, 5))
        ttk.Label(personal_frame, text="Format: +1 (555) 123-4567 or 5551234567", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Full Name
        ttk.Label(personal_frame, text="Full Name:").pack(anchor=W, pady=(15, 5))
        fullname_entry = ttk.Entry(personal_frame, font=('Arial', 12))
        fullname_entry.pack(fill=X, pady=(0, 15))
        
        # Organization
        ttk.Label(personal_frame, text="Organization:").pack(anchor=W, pady=(0, 5))
        org_entry = ttk.Entry(personal_frame, font=('Arial', 12))
        org_entry.pack(fill=X, pady=(0, 15))
        
        # Security Preferences section
        security_frame = ttk.LabelFrame(scrollable_frame, text="Security Preferences", padding=20)
        security_frame.pack(fill=X, pady=(0, 20))
        
        # 2FA preference
        twofa_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(security_frame, text="Enable Two-Factor Authentication (Recommended)", 
                       variable=twofa_var).pack(anchor=W, pady=2)
        
        # Auto-lock preference
        autolock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(security_frame, text="Enable Auto-Lock on inactivity", 
                       variable=autolock_var).pack(anchor=W, pady=2)
        
        # Terms and conditions
        terms_frame = ttk.LabelFrame(scrollable_frame, text="Terms & Conditions", padding=20)
        terms_frame.pack(fill=X, pady=(0, 20))
        
        # Scrollable terms text
        terms_container = ttk.Frame(terms_frame)
        terms_container.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        terms_text = tk.Text(terms_container, wrap=tk.WORD, font=('Arial', 9), height=6)
        terms_scrollbar = ttk.Scrollbar(terms_container, orient=VERTICAL, command=terms_text.yview)
        terms_text.configure(yscrollcommand=terms_scrollbar.set)
        
        terms_text.pack(side=LEFT, fill=BOTH, expand=True)
        terms_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Terms content
        terms_content = """
TERMS OF SERVICE AND PRIVACY POLICY

By creating an account with IronLock Vault, you agree to the following terms:

1. SECURITY RESPONSIBILITY
   - You are responsible for maintaining the security of your account
   - Never share your password or 2FA codes with anyone
   - Report any suspicious activity immediately

2. DATA PROTECTION
   - All data is encrypted using AES-256 encryption
   - We do not have access to your encrypted data
   - You are responsible for backing up your data

3. ACCEPTABLE USE
   - Use the service for legitimate purposes only
   - Do not store illegal or harmful content
   - Respect intellectual property rights

4. PRIVACY
   - We collect minimal data necessary for service operation
   - Access logs are maintained for security purposes
   - No personal data is shared with third parties

5. SERVICE AVAILABILITY
   - Service is provided "as is" without warranties
   - We strive for high availability but cannot guarantee 100% uptime
   - Regular maintenance may cause temporary service interruptions

6. ACCOUNT TERMINATION
   - We reserve the right to terminate accounts for violations
   - You may delete your account at any time
   - Data deletion is permanent and cannot be recovered

By checking the box below, you acknowledge that you have read and agree to these terms.
"""
        
        terms_text.insert(tk.END, terms_content)
        terms_text.config(state=tk.DISABLED)
        
        # Terms acceptance
        terms_var = tk.BooleanVar()
        ttk.Checkbutton(terms_frame, text="I have read and agree to the Terms of Service and Privacy Policy", 
                       variable=terms_var).pack(anchor=W)
        
        # Button frame
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=X, pady=(20, 0))
        
        def register():
            username = username_entry.get().strip()
            password = password_entry.get()
            confirm_password = confirm_password_entry.get()
            email = email_entry.get().strip() or None
            mobile_number = mobile_entry.get().strip() or None
            fullname = fullname_entry.get().strip() or None
            organization = org_entry.get().strip() or None
            
            # Validation
            if not username or not password:
                messagebox.showerror("Error", "Username and password are required")
                return
            
            if len(username) < 3 or len(username) > 20:
                messagebox.showerror("Error", "Username must be 3-20 characters long")
                return
            
            if not username.replace('_', '').replace('-', '').isalnum():
                messagebox.showerror("Error", "Username can only contain letters, numbers, underscores, and hyphens")
                return
            
            if password != confirm_password:
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            if len(password) < 8:
                messagebox.showerror("Error", "Password must be at least 8 characters long")
                return
            
            if not terms_var.get():
                messagebox.showerror("Error", "You must accept the Terms of Service to continue")
                return
            
            # Validate mobile number
            if mobile_number:
                is_valid, mobile_error = self.auth_manager.validate_mobile_number(mobile_number)
                if not is_valid:
                    messagebox.showerror("Error", mobile_error)
                    return
            
            # Additional user data
            user_data = {
                'fullname': fullname,
                'organization': organization,
                'enable_2fa': twofa_var.get(),
                'enable_autolock': autolock_var.get(),
                'registration_date': datetime.now().isoformat()
            }
            
            # Check if 2FA is enabled
            enable_2fa = user_data.get('enable_2fa', False)
            
            success, message = self.auth_manager.register_user(username, password, email, mobile_number, user_data, enable_2fa)
            
            if success:
                self.show_custom_success("Success", f"Account created successfully!\n\nWelcome to IronLock Vault, {username}!")
                register_window.destroy()
            else:
                self.show_custom_error("Registration Failed", message)
        
        # Register and Cancel buttons
        ttk.Button(button_frame, text="✅ Create Account", command=register, 
                  style='success.TButton').pack(side=LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Cancel", command=register_window.destroy, 
                  style='danger.TButton').pack(side=LEFT)
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(register_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            register_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                register_window.geometry("500x600")
                is_maximized = False
            else:
                register_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Focus on username entry
        username_entry.focus()
        
        # Bind Enter key to register
        register_window.bind('<Return>', lambda e: register())
        
        # Handle window close event
        def on_register_close():
            register_window.destroy()
        
        register_window.protocol("WM_DELETE_WINDOW", on_register_close)
    
    def login(self):
        """Handle login process"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.show_custom_error("Error", "Please enter username and password")
            return
        
        # Authenticate user
        success, message = self.auth_manager.authenticate_user(username, password)
        
        if success:
            self.current_user = self.auth_manager.current_user  # Set to user dict
            # Store password temporarily for encryption initialization
            self.current_password = password
            # Check if user has email or mobile configured for OTP
            has_email = self.current_user.get('email')
            has_mobile = self.current_user.get('mobile_number')
            
            if has_email or has_mobile:
                # Require OTP verification for login
                self.verify_otp_for_login()
            else:
                # No OTP configured, proceed with login
                self.complete_login()
        else:
            self.show_custom_error("Login Failed", message)
            self.password_entry.delete(0, tk.END)
    
    def complete_login(self):
        """Complete login process and show vault"""
        self.is_logged_in = True
        self.auth_manager.update_last_login(self.current_user['username'])
        self.logger.log_info(f"User logged in successfully: {self.current_user}")
        
        # Initialize encryption with user's password and salt
        try:
            # Ensure user has encryption salt (generate if missing for existing users)
            encryption_salt = self.auth_manager.ensure_encryption_salt(self.current_user['username'])
            
            if encryption_salt:
                # Convert base64 salt back to bytes
                import base64
                salt_bytes = base64.b64decode(encryption_salt)
                self.vault_manager.encryption_manager.initialize_encryption(self.current_password, salt_bytes)
                self.logger.log_info("Encryption initialized successfully")
            else:
                # Fallback for users without encryption salt (legacy users)
                self.vault_manager.encryption_manager.initialize_encryption(self.current_password)
                self.logger.log_info("Encryption initialized with fallback method")
        except Exception as e:
            self.logger.log_error(f"Failed to initialize encryption: {str(e)}")
            self.show_custom_error("Encryption Error", "Failed to initialize encryption. Please try logging in again.")
            return
        
        # Clear the stored password for security
        self.current_password = None
        
        # Check if this is the user's first login
        if self.is_user_first_login():
            self.show_first_login_setup()
        else:
            self.show_vault_ui()
    
    def verify_otp_for_login(self):
        """Show OTP verification dialog for login"""
        otp_window = tk.Toplevel(self.root)
        otp_window.title("Login Verification - OTP Required")
        otp_window.geometry("450x500")
        otp_window.transient(self.root)
        otp_window.grab_set()
        otp_window.resizable(True, True)
        
        # Center window
        otp_window.update_idletasks()
        x = (otp_window.winfo_screenwidth() // 2) - 225
        y = (otp_window.winfo_screenheight() // 2) - 250
        otp_window.geometry(f'450x500+{x}+{y}')
        
        # Main container with scrollbar
        main_container = ttk.Frame(otp_window)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Content frame
        frame = ttk.Frame(scrollable_frame, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(frame, text="🔐 Login Verification Required", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        ttk.Label(frame, text=f"Welcome back, {self.current_user['username']}! Please verify your identity to complete login.", 
                 font=('Arial', 11), wraplength=400).pack(pady=(0, 15))
        ttk.Label(frame, text="Choose a method to receive your OTP code:", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Determine available methods
        has_email = self.current_user.get('email')
        has_mobile = self.current_user.get('mobile_number')
        
        if not has_email and not has_mobile:
            ttk.Label(frame, text="❌ No email or mobile number configured for OTP delivery.", 
                     font=('Arial', 10), foreground='red').pack(pady=(0, 15))
            ttk.Label(frame, text="Please configure your email or mobile number in your profile settings first.", 
                     font=('Arial', 9), wraplength=400).pack(pady=(0, 15))
            ttk.Button(frame, text="Close", command=otp_window.destroy, style='danger.TButton').pack(pady=(10, 0))
            return
        
        method_var = tk.StringVar(value='Email' if has_email else 'SMS')
        
        # Method selection frame
        method_frame = ttk.LabelFrame(frame, text="OTP Delivery Method", padding=15)
        method_frame.pack(fill=X, pady=(0, 15))
        
        # Method selection
        if has_email:
            email_radio = ttk.Radiobutton(method_frame, text=f"📧 Email OTP", variable=method_var, value='Email')
            email_radio.pack(anchor=W, pady=2)
            ttk.Label(method_frame, text=f"   Send code to: {self.current_user.get('email')}", 
                     font=('Arial', 9), foreground='gray').pack(anchor=W, padx=(20, 0))
        
        if has_mobile:
            sms_radio = ttk.Radiobutton(method_frame, text=f"📱 SMS OTP", variable=method_var, value='SMS')
            sms_radio.pack(anchor=W, pady=2)
            ttk.Label(method_frame, text=f"   Send code to: {self.current_user.get('mobile_number')}", 
                     font=('Arial', 9), foreground='gray').pack(anchor=W, padx=(20, 0))
        
        # Send OTP button
        send_btn = ttk.Button(frame, text="📤 Send OTP Code", style='info.TButton')
        send_btn.pack(pady=(10, 15))
        
        # OTP verification frame (hidden until sent)
        verify_frame = ttk.LabelFrame(frame, text="Enter OTP Code", padding=15)
        otp_label = ttk.Label(verify_frame, text="Enter the 6-digit OTP code sent to your selected method:", 
                             font=('Arial', 10), wraplength=350)
        otp_entry = ttk.Entry(verify_frame, font=('Arial', 14), justify=CENTER, width=15)
        verify_btn = ttk.Button(verify_frame, text="✅ Complete Login", style='success.TButton')
        resend_btn = ttk.Button(verify_frame, text="🔄 Resend OTP", style='secondary.TButton')
        
        def send_otp():
            method = method_var.get()
            if method == 'Email':
                success, msg = self.auth_manager.generate_email_otp()
            else:
                success, msg = self.auth_manager.generate_mobile_otp()
            if success:
                self.show_custom_info("OTP Sent", msg)
                verify_frame.pack(fill=X, pady=(0, 15))
                otp_label.pack(pady=(0, 10))
                otp_entry.pack(pady=(0, 15))
                verify_btn.pack(pady=(0, 5))
                resend_btn.pack(pady=(0, 5))
                otp_entry.focus()
                # Scroll to show the verification frame
                canvas.yview_moveto(1)
            else:
                self.show_custom_error("Error", msg)
        
        def verify_otp():
            code = otp_entry.get().strip()
            method = method_var.get()
            if not code:
                self.show_custom_error("Error", "Please enter the OTP code")
                return
            if len(code) != 6:
                self.show_custom_error("Error", "OTP code must be 6 digits")
                return
            if method == 'Email':
                valid = self.auth_manager.verify_email_otp(code)
            else:
                valid = self.auth_manager.verify_mobile_otp(code)
            if valid:
                otp_window.destroy()
                self.complete_login()
            else:
                self.show_custom_error("Verification Failed", "Invalid or expired OTP code")
                otp_entry.delete(0, tk.END)
        
        send_btn.config(command=send_otp)
        verify_btn.config(command=verify_otp)
        resend_btn.config(command=send_otp)
        otp_entry.bind('<Return>', lambda e: verify_otp())
        
        # Bottom buttons frame
        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill=X, pady=(15, 0))
        
        ttk.Button(bottom_frame, text="❌ Cancel Login", command=lambda: self.cancel_login(otp_window), 
                  style='danger.TButton').pack(side=RIGHT)
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(otp_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            otp_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                otp_window.geometry("450x500")
                is_maximized = False
            else:
                otp_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Unbind mousewheel when window closes
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            self.cancel_login(otp_window)
        
        otp_window.protocol("WM_DELETE_WINDOW", on_closing)
    
    def cancel_login(self, otp_window):
        """Cancel login process and return to login screen"""
        # Clear current user and password
        self.current_user = None
        self.current_password = None
        self.auth_manager.logout()
        
        # Clear password entry
        self.password_entry.delete(0, tk.END)
        
        # Close OTP window
        otp_window.destroy()
        
        # Show message
        self.show_custom_info("Login Cancelled", "Login process has been cancelled. Please try again.")
    
    def is_user_first_login(self):
        """Check if this is the user's first login"""
        try:
            conn = self.auth_manager.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT last_login FROM users WHERE username = ?", (self.current_user['username'],))
            result = cursor.fetchone()
            conn.close()
            
            # If last_login is None, it's the first login
            return result and result[0] is None
        except Exception as e:
            self.logger.log_error(f"Error checking first login: {str(e)}")
            return False
    
    def show_first_login_setup(self):
        """Show first login setup instructions"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🎉 Welcome to IronLock Vault!", 
            font=('Arial', 24, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text=f"Welcome back, {self.current_user}! Let's set up your 2FA.",
            font=('Arial', 12),
            foreground='gray'
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Setup instructions frame
        setup_frame = ttk.LabelFrame(main_frame, text="Two-Factor Authentication Setup", padding=20)
        setup_frame.pack(fill=X, pady=20, padx=50)
        
        # Instructions
        instructions = [
            "🔐 Your account is now protected with two-factor authentication.",
            "",
            "📱 To complete setup, you need to:",
            "1. Download an authenticator app (Google Authenticator, Authy, etc.)",
            "2. Scan the QR code or enter the setup key",
            "3. Use the 6-digit code from the app to verify",
            "",
            "💡 This adds an extra layer of security to your vault."
        ]
        
        for instruction in instructions:
            if instruction.startswith("🔐") or instruction.startswith("📱") or instruction.startswith("💡"):
                ttk.Label(
                    setup_frame,
                    text=instruction,
                    font=('Arial', 11, 'bold')
                ).pack(anchor=W, pady=2)
            elif instruction.startswith("1.") or instruction.startswith("2.") or instruction.startswith("3."):
                ttk.Label(
                    setup_frame,
                    text=instruction,
                    font=('Arial', 10)
                ).pack(anchor=W, pady=1, padx=(20, 0))
            else:
                ttk.Label(
                    setup_frame,
                    text=instruction,
                    font=('Arial', 10)
                ).pack(anchor=W, pady=2)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(pady=30)
        
        # Show QR code button
        ttk.Button(
            buttons_frame,
            text="📱 Show QR Code",
            command=self.show_qr_code,
            style='info.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        # Skip for now button
        ttk.Button(
            buttons_frame,
            text="⏭️ Skip for Now",
            command=self.show_vault_ui,
            style='secondary.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        # Continue to vault button
        ttk.Button(
            buttons_frame,
            text="🚀 Continue to Vault",
            command=self.show_vault_ui,
            style='success.TButton'
        ).pack(side=LEFT)
        
        # Encryption will be initialized during login process
        
        self.show_vault_ui()
    
    def show_vault_ui(self):
        """Show main vault interface with simplified layout and popup dialogs"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Setup activity tracking for auto-lock
        self.setup_activity_tracking(main_container)
        
        # Create main vault interface (no tabs)
        self.create_main_vault_interface(main_container)
        
        # Status bar
        self.create_status_bar(main_container)
        
        # Load vault items
        self.refresh_vault_items()

    def create_main_vault_interface(self, parent):
        """Create the main vault interface without tabs"""
        # Create toolbar
        self.create_toolbar(parent)
        
        # Main content frame
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for adding items
        left_panel = ttk.LabelFrame(content_frame, text="Add Items", padding=15)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=10)
        self.create_add_items_panel(left_panel)
        
        # Right panel for vault items
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.create_vault_items_panel(right_panel)

    def create_toolbar(self, parent):
        """Create toolbar with buttons for popup dialogs"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=10, pady=10)
        actions_frame = ttk.Frame(toolbar)
        actions_frame.pack(side=tk.RIGHT)
        btns = [
            ("📋 Select All", self.select_all_items, 'info.TButton', "Select all items in the vault."),
            ("❌ Unselect All", self.unselect_all_items, 'secondary.TButton', "Unselect all items in the vault."),
            ("🔍 Search", self.show_search_dialog, 'info.TButton', "Search for items in your vault."),
            ("📊 Logs", self.show_logs_dialog, 'warning.TButton', "View access and activity logs."),
            ("⚙️ Settings", self.show_settings_dialog, 'secondary.TButton', "Open settings and preferences."),
            ("🔒 Lock Vault", self.lock_vault, 'danger.TButton', "Lock the vault immediately."),
            ("❓ Help", self.show_help_dialog, 'info.TButton', "Show help and documentation."),
            ("🔄 Refresh", self.refresh_vault_items, 'info.TButton', "Refresh the vault item list.")
        ]
        for text, cmd, style, tip in btns:
            btn = ttk.Button(actions_frame, text=text, command=cmd, style=style)
            btn.pack(side=tk.LEFT, padx=4)
            Tooltip(btn, tip)





    def show_settings_dialog(self, parent=None, as_tab=False):
        """Show settings dialog as popup window"""
        # Create popup window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings - IronLock Vault")
        settings_window.geometry("800x600")
        settings_window.transient(self.root)
        settings_window.grab_set()
        settings_window.resizable(True, True)
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - 400
        y = (settings_window.winfo_screenheight() // 2) - 300
        settings_window.geometry(f'800x600+{x}+{y}')
        
        # Main container
        main_container = ttk.Frame(settings_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Sidebar
        sidebar = ttk.Frame(main_container, width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20), pady=20)
        sidebar.pack_propagate(False)
        
        # Content container
        content_container = ttk.Frame(main_container)
        content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20), pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(content_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Tabs and icons
        tab_defs = [
            ("Security", "🔒"),
            ("Profile", "👤"),
            ("Account Security", "🔐"),
            ("General", "⚙️"),
            ("Advanced", "🔧")
        ]
        tab_frames = {}
        selected_tab = tk.StringVar(value=tab_defs[0][0])

        # --- Create all tab frames first ---
        security_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Security"] = security_frame
        profile_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Profile"] = profile_frame
        account_security_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Account Security"] = account_security_frame
        general_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["General"] = general_frame
        advanced_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Advanced"] = advanced_frame

        def show_tab(tab_name):
            for name, frame in tab_frames.items():
                frame.pack_forget()
            tab_frames[tab_name].pack(fill=tk.BOTH, expand=True)
            selected_tab.set(tab_name)

        # Sidebar navigation buttons
        for tab_name, icon in tab_defs:
            btn = ttk.Button(
                sidebar,
                text=f"{icon}  {tab_name}",
                style='TButton',
                command=lambda n=tab_name: show_tab(n)
            )
            btn.pack(fill=tk.X, pady=6, anchor=tk.N)

        # --- Security Tab ---
        ttk.Label(security_frame, text="🔒 Security Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(security_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        timeout_frame = ttk.LabelFrame(security_frame, text="Auto-Lock Settings", padding=15)
        timeout_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(timeout_frame, text="Auto-lock timeout (minutes):").pack(anchor=tk.W, pady=(0, 5))
        timeout_var = tk.StringVar(value=str(self.config.get('auto_lock_timeout', 300) // 60))
        timeout_entry = ttk.Entry(timeout_frame, textvariable=timeout_var, width=10)
        timeout_entry.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(timeout_frame, text="Set to 0 to disable auto-lock", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        twofa_frame = ttk.LabelFrame(security_frame, text="Two-Factor Authentication", padding=15)
        twofa_frame.pack(fill=tk.X, pady=(0, 15))
        require_2fa_var = tk.BooleanVar(value=self.config.get('require_2fa', True))
        twofa_check = ttk.Checkbutton(twofa_frame, text="Require 2FA for all actions", variable=require_2fa_var)
        twofa_check.pack(anchor=tk.W, pady=2)
        has_2fa = self.auth_manager.current_user and self.auth_manager.current_user.get('totp_secret')
        if has_2fa:
            ttk.Label(twofa_frame, text="✅ 2FA is enabled for your account", font=('Arial', 10), foreground='green').pack(anchor=tk.W, pady=5)
        else:
            ttk.Label(twofa_frame, text="❌ 2FA is not enabled for your account", font=('Arial', 10), foreground='red').pack(anchor=tk.W, pady=5)
            setup_2fa_btn = ttk.Button(twofa_frame, text="🔐 Set Up 2FA Now", command=self.show_2fa_setup_dialog, style='success.TButton')
            setup_2fa_btn.pack(anchor=tk.W, pady=5)
        password_frame = ttk.LabelFrame(security_frame, text="Change Master Password", padding=15)
        password_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(password_frame, text="Change your master password:").pack(anchor=tk.W, pady=(0, 5))
        old_pass_var = tk.StringVar()
        new_pass_var = tk.StringVar()
        confirm_pass_var = tk.StringVar()
        ttk.Label(password_frame, text="Current Password:").pack(anchor=tk.W)
        old_pass_entry = ttk.Entry(password_frame, textvariable=old_pass_var, show='*')
        old_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(password_frame, text="New Password:").pack(anchor=tk.W)
        new_pass_entry = ttk.Entry(password_frame, textvariable=new_pass_var, show='*')
        new_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(password_frame, text="Confirm New Password:").pack(anchor=tk.W)
        confirm_pass_entry = ttk.Entry(password_frame, textvariable=confirm_pass_var, show='*')
        confirm_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        def change_password():
            old = old_pass_var.get()
            new = new_pass_var.get()
            confirm = confirm_pass_var.get()
            if not old or not new or not confirm:
                messagebox.showerror("Error", "All password fields are required.")
                return
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.")
                return
            if self.auth_manager.current_user:
                username = self.auth_manager.current_user.get('username')
                success, msg = self.auth_manager.perform_password_change(old, new)
                if success:
                    messagebox.showinfo("Success", "Password changed successfully.")
                    old_pass_var.set("")
                    new_pass_var.set("")
                    confirm_pass_var.set("")
                else:
                    messagebox.showerror("Error", msg)
            else:
                messagebox.showerror("Error", "No user logged in.")
        ttk.Button(password_frame, text="Change Password", command=change_password, style='success.TButton').pack(anchor=tk.W, pady=(5, 0))
        bio_frame = ttk.LabelFrame(security_frame, text="Biometric Unlock", padding=15)
        bio_frame.pack(fill=tk.X, pady=(0, 15))
        bio_var = tk.BooleanVar(value=self.config.get('enable_biometric', False))
        bio_check = ttk.Checkbutton(bio_frame, text="Enable biometric unlock (fingerprint/face)", variable=bio_var, state='disabled')
        bio_check.pack(anchor=tk.W, pady=2)
        ttk.Label(bio_frame, text="(Biometric unlock support coming soon)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        alerts_frame = ttk.LabelFrame(security_frame, text="Email Alerts", padding=15)
        alerts_frame.pack(fill=tk.X, pady=(0, 15))
        alerts_var = tk.BooleanVar(value=self.config.get('enable_email_alerts', False))
        alerts_check = ttk.Checkbutton(alerts_frame, text="Enable email alerts for suspicious activity", variable=alerts_var)
        alerts_check.pack(anchor=tk.W, pady=2)

        # --- Profile Tab ---
        ttk.Label(profile_frame, text="👤 User Profile", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(profile_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        personal_frame = ttk.LabelFrame(profile_frame, text="Personal Information", padding=15)
        personal_frame.pack(fill=tk.X, pady=(0, 20))
        user_profile = None
        if self.auth_manager.current_user:
            username = self.auth_manager.current_user.get('username')
            user_profile = self.auth_manager.get_user_profile(username)
        else:
            username = None
        ttk.Label(personal_frame, text="Email Address:").pack(anchor=tk.W, pady=(0, 5))
        email_var = tk.StringVar(value=(user_profile['email'] if user_profile and user_profile.get('email') else ''))
        email_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=email_var)
        email_entry.pack(fill=tk.X, pady=(0, 5))
        email_feedback = ttk.Label(personal_frame, text="", font=('Arial', 9))
        email_feedback.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(personal_frame, text="Used for password recovery and 2FA", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        ttk.Label(personal_frame, text="Mobile Number:").pack(anchor=tk.W, pady=(0, 5))
        mobile_var = tk.StringVar(value=(user_profile['mobile_number'] if user_profile and user_profile.get('mobile_number') else ''))
        mobile_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=mobile_var)
        mobile_entry.pack(fill=tk.X, pady=(0, 5))
        mobile_feedback = ttk.Label(personal_frame, text="", font=('Arial', 9))
        mobile_feedback.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(personal_frame, text="Format: +1 (555) 123-4567 or 5551234567", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        ttk.Label(personal_frame, text="Full Name:").pack(anchor=tk.W, pady=(15, 5))
        fullname_var = tk.StringVar(value=(user_profile['user_data'].get('fullname') if user_profile and user_profile.get('user_data') and user_profile['user_data'].get('fullname') else ''))
        fullname_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=fullname_var)
        fullname_entry.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(personal_frame, text="Organization:").pack(anchor=tk.W, pady=(0, 5))
        org_var = tk.StringVar(value=(user_profile['user_data'].get('organization') if user_profile and user_profile.get('user_data') and user_profile['user_data'].get('organization') else ''))
        org_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=org_var)
        org_entry.pack(fill=tk.X, pady=(0, 15))
        def validate_email(*args):
            email = email_var.get().strip()
            if not email:
                email_feedback.config(text="", foreground="black")
                email_entry.config(foreground="black")
                return
            pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if re.match(pattern, email):
                email_feedback.config(text="✔ Valid email", foreground="green")
                email_entry.config(foreground="green")
            else:
                email_feedback.config(text="✖ Invalid email format", foreground="red")
                email_entry.config(foreground="red")
        email_var.trace_add('write', validate_email)
        def validate_mobile(*args):
            mobile = mobile_var.get().strip()
            if not mobile:
                mobile_feedback.config(text="", foreground="black")
                mobile_entry.config(foreground="black")
                return
            pattern = r"^(\+\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}$"
            if re.match(pattern, mobile):
                mobile_feedback.config(text="✔ Valid phone number", foreground="green")
                mobile_entry.config(foreground="green")
            else:
                mobile_feedback.config(text="✖ Invalid phone number", foreground="red")
                mobile_entry.config(foreground="red")
        mobile_var.trace_add('write', validate_mobile)
        def save_profile():
            if not username:
                messagebox.showerror("Error", "No user logged in.")
                return
            user_data = user_profile['user_data'] if user_profile and user_profile.get('user_data') else {}
            user_data['fullname'] = fullname_var.get()
            user_data['organization'] = org_var.get()
            success, msg = self.auth_manager.update_user_profile(
                username,
                email=email_var.get(),
                mobile_number=mobile_var.get(),
                user_data=user_data
            )
            if success:
                messagebox.showinfo("Profile Updated", "Your profile has been updated successfully.")
            else:
                messagebox.showerror("Error", msg)
        ttk.Button(personal_frame, text="Save Profile", command=save_profile, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))

        # --- Account Security Tab ---
        ttk.Label(account_security_frame, text="🔐 Account Security Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(account_security_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        pw_frame = ttk.LabelFrame(account_security_frame, text="Change Password", padding=15)
        pw_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(pw_frame, text="Change your account password:").pack(anchor=tk.W, pady=(0, 5))
        acc_old_pass_var = tk.StringVar()
        acc_new_pass_var = tk.StringVar()
        acc_confirm_pass_var = tk.StringVar()
        ttk.Label(pw_frame, text="Current Password:").pack(anchor=tk.W)
        acc_old_pass_entry = ttk.Entry(pw_frame, textvariable=acc_old_pass_var, show='*')
        acc_old_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(pw_frame, text="New Password:").pack(anchor=tk.W)
        acc_new_pass_entry = ttk.Entry(pw_frame, textvariable=acc_new_pass_var, show='*')
        acc_new_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(pw_frame, text="Confirm New Password:").pack(anchor=tk.W)
        acc_confirm_pass_entry = ttk.Entry(pw_frame, textvariable=acc_confirm_pass_var, show='*')
        acc_confirm_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        def acc_change_password():
            old = acc_old_pass_var.get()
            new = acc_new_pass_var.get()
            confirm = acc_confirm_pass_var.get()
            if not old or not new or not confirm:
                messagebox.showerror("Error", "All password fields are required.")
                return
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.")
                return
            if self.auth_manager.current_user:
                username = self.auth_manager.current_user.get('username')
                success, msg = self.auth_manager.perform_password_change(old, new)
                if success:
                    messagebox.showinfo("Success", "Password changed successfully.")
                    acc_old_pass_var.set("")
                    acc_new_pass_var.set("")
                    acc_confirm_pass_var.set("")
                else:
                    messagebox.showerror("Error", msg)
            else:
                messagebox.showerror("Error", "No user logged in.")
        ttk.Button(pw_frame, text="Change Password", command=acc_change_password, style='success.TButton').pack(anchor=tk.W, pady=(5, 0))
        twofa_frame = ttk.LabelFrame(account_security_frame, text="Two-Factor Authentication (2FA)", padding=15)
        twofa_frame.pack(fill=tk.X, pady=(0, 15))
        has_2fa = self.auth_manager.current_user and self.auth_manager.current_user.get('totp_secret')
        if has_2fa:
            ttk.Label(twofa_frame, text="✅ 2FA is enabled for your account", font=('Arial', 10), foreground='green').pack(anchor=tk.W, pady=5)
            ttk.Button(twofa_frame, text="Disable 2FA", command=lambda: messagebox.showinfo("Coming Soon", "Disabling 2FA will be available in a future update."), style='danger.TButton').pack(anchor=tk.W, pady=2)
            ttk.Button(twofa_frame, text="Reset 2FA (Lost Device)", command=lambda: messagebox.showinfo("Coming Soon", "2FA reset will be available in a future update."), style='warning.TButton').pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(twofa_frame, text="❌ 2FA is not enabled for your account", font=('Arial', 10), foreground='red').pack(anchor=tk.W, pady=5)
            ttk.Button(twofa_frame, text="Enable 2FA", command=self.show_2fa_setup_dialog, style='success.TButton').pack(anchor=tk.W, pady=2)
        login_frame = ttk.LabelFrame(account_security_frame, text="Recent Login Activity", padding=15)
        login_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(login_frame, text="(Recent login activity will appear here in a future update.)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)

        # --- General Tab ---
        ttk.Label(general_frame, text="⚙️ General Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(general_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        theme_frame = ttk.LabelFrame(general_frame, text="Theme", padding=15)
        theme_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(theme_frame, text="Select application theme:").pack(anchor=tk.W)
        theme_var = tk.StringVar(value=self.config.get('theme', 'darkly'))
        theme_options = ['darkly', 'flatly', 'cosmo', 'cyborg', 'journal', 'litera', 'lumen', 'minty', 'pulse', 'sandstone', 'simplex', 'slate', 'solar', 'spacelab', 'superhero', 'united', 'yeti']
        theme_menu = ttk.Combobox(theme_frame, textvariable=theme_var, values=theme_options, state='readonly')
        theme_menu.pack(anchor=tk.W, pady=(5, 0))
        lang_frame = ttk.LabelFrame(general_frame, text="Language", padding=15)
        lang_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(lang_frame, text="Select application language:").pack(anchor=tk.W)
        lang_var = tk.StringVar(value='English')
        lang_menu = ttk.Combobox(lang_frame, textvariable=lang_var, values=['English'], state='readonly')
        lang_menu.pack(anchor=tk.W, pady=(5, 0))
        ttk.Label(lang_frame, text="(More languages coming soon)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        win_frame = ttk.LabelFrame(general_frame, text="Window Size", padding=15)
        win_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(win_frame, text="Set main window size (e.g., 1200x800):").pack(anchor=tk.W)
        window_size_var = tk.StringVar(value=self.config.get('window_size', '1200x800'))
        window_size_entry = ttk.Entry(win_frame, textvariable=window_size_var)
        window_size_entry.pack(anchor=tk.W, pady=(5, 0))
        notif_frame = ttk.LabelFrame(general_frame, text="Notifications", padding=15)
        notif_frame.pack(fill=tk.X, pady=(0, 15))
        notif_var = tk.BooleanVar(value=False)
        notif_check = ttk.Checkbutton(notif_frame, text="Enable desktop notifications (coming soon)", variable=notif_var, state='disabled')
        notif_check.pack(anchor=tk.W, pady=2)
        def save_general():
            self.config.set('theme', theme_var.get())
            self.config.set('window_size', window_size_var.get())
            messagebox.showinfo("General Settings Saved", "Theme and window size have been saved. Please restart the app to apply theme changes.")
        ttk.Button(general_frame, text="Save General Settings", command=save_general, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))

        # --- Advanced Tab ---
        ttk.Label(advanced_frame, text="🔧 Advanced Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(advanced_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        vault_frame = ttk.LabelFrame(advanced_frame, text="Vault Data", padding=15)
        vault_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Button(vault_frame, text="Export Vault Data", command=lambda: messagebox.showinfo("Coming Soon", "Vault export will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(vault_frame, text="Import Vault Data", command=lambda: messagebox.showinfo("Coming Soon", "Vault import will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        backup_frame = ttk.LabelFrame(advanced_frame, text="Backup & Restore", padding=15)
        backup_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Button(backup_frame, text="Backup Now", command=lambda: messagebox.showinfo("Coming Soon", "Backup will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(backup_frame, text="Restore Backup", command=lambda: messagebox.showinfo("Coming Soon", "Restore will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        log_frame = ttk.LabelFrame(advanced_frame, text="Logging", padding=15)
        log_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(log_frame, text="Log level:").pack(anchor=tk.W)
        log_level_var = tk.StringVar(value=self.config.get('log_level', 'INFO'))
        log_level_menu = ttk.Combobox(log_frame, textvariable=log_level_var, values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], state='readonly')
        log_level_menu.pack(anchor=tk.W, pady=(5, 0))
        debug_var = tk.BooleanVar(value=self.config.get('debug_mode', False))
        debug_check = ttk.Checkbutton(log_frame, text="Enable debug mode", variable=debug_var)
        debug_check.pack(anchor=tk.W, pady=2)
        def save_advanced():
            self.config.set('log_level', log_level_var.get())
            self.config.set('debug_mode', debug_var.get())
            messagebox.showinfo("Advanced Settings Saved", "Log level and debug mode have been saved.")
        ttk.Button(advanced_frame, text="Save Advanced Settings", command=save_advanced, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))
        ttk.Button(advanced_frame, text="Reset All Settings to Default", command=lambda: messagebox.showinfo("Coming Soon", "Reset to defaults will be available in a future update."), style='danger.TButton').pack(anchor=tk.E, pady=(10, 0))

        show_tab(tab_defs[0][0])
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(settings_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            settings_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                settings_window.geometry("800x600")
                is_maximized = False
            else:
                settings_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Close button
        ttk.Button(control_frame, text="Close", command=settings_window.destroy, style='secondary.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_settings_close():
            settings_window.destroy()
        
        settings_window.protocol("WM_DELETE_WINDOW", on_settings_close)
    def show_logs_dialog(self, parent=None, as_tab=False):
        """Show logs dialog as popup window"""
        # Create popup window
        logs_window = tk.Toplevel(self.root)
        logs_window.title("Logs - IronLock Vault")
        logs_window.geometry("1000x700")
        logs_window.transient(self.root)
        logs_window.grab_set()
        logs_window.resizable(True, True)
        
        # Center the window
        logs_window.update_idletasks()
        x = (logs_window.winfo_screenwidth() // 2) - 500
        y = (logs_window.winfo_screenheight() // 2) - 350
        logs_window.geometry(f'1000x700+{x}+{y}')
        
        # Main container
        main_container = ttk.Frame(logs_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create notebook for tabs
        import csv
        from tkinter import simpledialog
        notebook = ttk.Notebook(main_container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        access_frame = ttk.Frame(notebook)
        notebook.add(access_frame, text="Access Logs")
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Security Logs")
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="System Logs")

        # Analytics/Stats Panel
        stats_frame = ttk.LabelFrame(logs_window, text="Log Analytics & Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        stats_label = ttk.Label(stats_frame, text="", font=("Consolas", 11))
        stats_label.pack(anchor=tk.W)

        # Controls (shared)
        control_frame = ttk.Frame(logs_window)
        control_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0,10))
        ttk.Label(control_frame, text="Date from:").pack(side=tk.LEFT)
        date_from_var = tk.StringVar()
        date_from_entry = ttk.Entry(control_frame, textvariable=date_from_var, width=12)
        date_from_entry.pack(side=tk.LEFT, padx=(0,5))
        ttk.Label(control_frame, text="to").pack(side=tk.LEFT)
        date_to_var = tk.StringVar()
        date_to_entry = ttk.Entry(control_frame, textvariable=date_to_var, width=12)
        date_to_entry.pack(side=tk.LEFT, padx=(0,10))
        ttk.Label(control_frame, text="User:").pack(side=tk.LEFT)
        user_var = tk.StringVar(value="All")
        user_entry = ttk.Entry(control_frame, textvariable=user_var, width=12)
        user_entry.pack(side=tk.LEFT, padx=(0,10))
        auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_btn = ttk.Checkbutton(control_frame, text="Auto-Refresh", variable=auto_refresh_var)
        auto_refresh_btn.pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(control_frame, text="Export CSV", command=lambda: self.export_logs_to_csv(all_logs)).pack(side=tk.RIGHT, padx=(0,5))
        ttk.Button(control_frame, text="Export JSON", command=lambda: self.export_logs_to_json(all_logs)).pack(side=tk.RIGHT, padx=(0,5))

        # Treeview setup helper
        def setup_tree(parent, columns, headings):
            tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
            for col, head in zip(columns, headings):
                tree.heading(col, text=head)
                tree.column(col, width=160, minwidth=80)
            v_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
            h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
            tree.grid(row=0, column=0, sticky='nsew')
            v_scroll.grid(row=0, column=1, sticky='ns')
            h_scroll.grid(row=1, column=0, sticky='ew')
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
            return tree

        # Load all logs (access, security, system/info)
        all_logs = []
        def load_all_logs():
            nonlocal all_logs
            access_logs = self.vault_manager.get_access_logs(self.current_user['username'], limit=500)
            for log in access_logs:
                log['level'] = 'INFO' if log.get('success', True) else 'WARNING'
                log['type'] = 'Access'
                log['user'] = self.current_user['username']
            security_logs = self.logger.get_recent_logs(hours=168, level='SECURITY')
            for log in security_logs:
                log['level'] = 'SECURITY'
                log['type'] = 'Security'
                log['user'] = log.get('user', self.current_user['username'])
            system_logs = self.logger.get_recent_logs(hours=168)
            for log in system_logs:
                if log['level'] not in ('SECURITY',):
                    log['type'] = 'System'
                    log['user'] = log.get('user', self.current_user['username'])
            all_logs = access_logs + security_logs + [l for l in system_logs if l['level'] != 'SECURITY']

        # Filtering and search
        def filter_logs(logs, log_type):
            q = search_var.get().lower()
            df = date_from_var.get().strip()
            dt = date_to_var.get().strip()
            user = user_var.get().strip()
            filtered = []
            for log in logs:
                if log_type and log.get('type') != log_type:
                    continue
                if q and q not in str(log).lower():
                    continue
                if user and user != 'All' and user.lower() not in str(log.get('user', '')).lower():
                    continue
                log_time = log.get('timestamp') or log.get('access_time')
                if log_time:
                    try:
                        from datetime import datetime
                        log_dt = datetime.fromisoformat(log_time[:19])
                        if df:
                            df_dt = datetime.fromisoformat(df)
                            if log_dt < df_dt:
                                continue
                        if dt:
                            dt_dt = datetime.fromisoformat(dt)
                            if log_dt > dt_dt:
                                continue
                    except Exception:
                        pass
                    filtered.append(log)
                return filtered

            # Treeviews for each tab
            access_tree = setup_tree(access_frame, ['Item', 'Time', 'Type', 'Status', 'User'], ['Item', 'Time', 'Type', 'Status', 'User'])
            security_tree = setup_tree(security_frame, ['Time', 'Level', 'Event', 'Message', 'User'], ['Time', 'Level', 'Event', 'Message', 'User'])
            system_tree = setup_tree(system_frame, ['Time', 'Level', 'Message', 'User'], ['Time', 'Level', 'Message', 'User'])

            # Populate trees
            def refresh_all():
                load_all_logs()
                access_tree.delete(*access_tree.get_children())
                for log in filter_logs(all_logs, 'Access'):
                    status = "✅ Success" if log.get('success', True) else "❌ Failed"
                    access_tree.insert('', 'end', values=(log.get('item_name',''), log.get('access_time',''), log.get('access_type',''), status, log.get('user','')), tags=(log.get('level','INFO'),))
                security_tree.delete(*security_tree.get_children())
                for log in filter_logs(all_logs, 'Security'):
                    security_tree.insert('', 'end', values=(log.get('timestamp',''), log.get('level',''), log.get('event_type',''), log.get('message',''), log.get('user','')), tags=(log.get('level','SECURITY'),))
                system_tree.delete(*system_tree.get_children())
                for log in filter_logs(all_logs, 'System'):
                    system_tree.insert('', 'end', values=(log.get('timestamp',''), log.get('level',''), log.get('message',''), log.get('user','')), tags=(log.get('level','INFO'),))
                stats = self.logger.get_security_summary()
                stats_text = f"Total Security Events: {stats.get('total_security_events',0)}\nFailed Logins: {stats.get('failed_logins',0)}\nTamper Attempts: {stats.get('tamper_attempts',0)}\nSuspicious Access: {stats.get('suspicious_access',0)}\n\nRecent Security Events:\n" + '\n'.join([f"{e.get('timestamp','')}: {e.get('event_type','')} - {e.get('message','')}" for e in stats.get('last_24h_events',[])])
                stats_label.config(text=stats_text)

            # Color rows by log level
            def get_log_color(level):
                if level in ("ERROR", "SECURITY"): return "#ffcccc"
                if level == "WARNING": return "#fff2cc"
                if level == "INFO": return "#e6f7ff"
                return "#f4f4f4"
            def colorize_tree(tree):
                for iid in tree.get_children():
                    level = tree.item(iid, 'tags')[0] if tree.item(iid, 'tags') else 'INFO'
                    tree.tag_configure(level, background=get_log_color(level))

            # Double-click for details
            def show_log_details(event, tree):
                item = tree.focus()
                if not item:
                    return
                values = tree.item(item, 'values')
                detail = '\n'.join(f"{col}: {val}" for col, val in zip(tree['columns'], values))
                messagebox.showinfo("Log Details", detail)
            for tree in [access_tree, security_tree, system_tree]:
                tree.bind('<Double-1>', lambda e, t=tree: show_log_details(e, t))

            # Export helpers
            def export_logs_to_csv(logs):
                file = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV Files', '*.csv')])
                if not file:
                    return
                if not logs:
                    messagebox.showwarning("No logs", "No logs to export.")
                    return
                keys = set()
                for log in logs:
                    keys.update(log.keys())
                keys = list(keys)
                with open(file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(logs)
                messagebox.showinfo("Exported", f"Logs exported to {file}")
            def export_logs_to_json(logs):
                file = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files', '*.json')])
                if not file:
                    return
                if not logs:
                    messagebox.showwarning("No logs", "No logs to export.")
                    return
                import json
                with open(file, 'w', encoding='utf-8') as f:
                    json.dump(logs, f, indent=2)
                messagebox.showinfo("Exported", f"Logs exported to {file}")
            self.export_logs_to_csv = export_logs_to_csv
            self.export_logs_to_json = export_logs_to_json

            # Refresh logic
            def periodic_refresh():
                if auto_refresh_var.get():
                    refresh_all()
                    colorize_tree(access_tree)
                    colorize_tree(security_tree)
                    colorize_tree(system_tree)
                parent.after(5000, periodic_refresh)
            periodic_refresh()

            # Manual refresh and search triggers
            search_var.trace('w', lambda *a: refresh_all())
            date_from_var.trace('w', lambda *a: refresh_all())
            date_to_var.trace('w', lambda *a: refresh_all())
            user_var.trace('w', lambda *a: refresh_all())
            auto_refresh_var.trace('w', lambda *a: refresh_all())

            # Initial load
            refresh_all()
            
            # Add control buttons at the bottom
            control_frame = ttk.Frame(logs_window)
            control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            # Left side - Window control buttons
            window_controls = ttk.Frame(control_frame)
            window_controls.pack(side=tk.LEFT)
            
            # Minimize button
            def minimize_window():
                logs_window.iconify()
            ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Maximize/Restore button
            is_maximized = False
            def toggle_maximize():
                nonlocal is_maximized
                if is_maximized:
                    logs_window.geometry("1000x700")
                    is_maximized = False
                else:
                    logs_window.state('zoomed')
                    is_maximized = True
            ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Right side - Close button
            ttk.Button(control_frame, text="Close", command=logs_window.destroy, style='secondary.TButton').pack(side=tk.RIGHT)
            
            # Handle window close event
            def on_logs_close():
                logs_window.destroy()
            
            logs_window.protocol("WM_DELETE_WINDOW", on_logs_close)
    def show_help_dialog(self, parent=None, as_tab=False):
        """Show help dialog as popup window"""
        # Create popup window
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - IronLock Vault")
        help_window.geometry("900x700")
        help_window.transient(self.root)
        help_window.grab_set()
        help_window.resizable(True, True)
        
        # Center the window
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - 450
        y = (help_window.winfo_screenheight() // 2) - 350
        help_window.geometry(f'900x700+{x}+{y}')
        
        # Main container
        main_container = ttk.Frame(help_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Navigation frame
        nav_frame = ttk.Frame(main_container, width=200)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0), pady=20)
        nav_frame.pack_propagate(False)
        nav_label = ttk.Label(nav_frame, text="Sections", font=('Arial', 12, 'bold'))
        nav_label.pack(anchor=tk.NW, pady=(0, 10))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(nav_frame, textvariable=search_var, width=18)
        search_entry.pack(anchor=tk.NW, pady=(10, 10))
        search_entry.insert(0, "Search help...")
        def clear_search(event):
            if search_entry.get() == "Search help...":
                search_entry.delete(0, tk.END)
        search_entry.bind('<FocusIn>', clear_search)
        content_frame = ttk.Frame(main_container)
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20), pady=20)
        canvas = tk.Canvas(content_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        section_labels = {}
        def add_section(title, icon=None):
            anchor = title.upper()
            label = ttk.Label(scrollable_frame, text=f"{icon+' ' if icon else ''}{title}", font=('Arial', 15, 'bold'))
            label.pack(anchor=tk.W, pady=(30, 8))
            section_labels[anchor] = label
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
            help_sections = [
                ("Overview", "📋", "IronLock Vault is a secure desktop application that allows you to store and manage sensitive files, folders, and applications with military-grade encryption and two-factor authentication."),
                ("Security Features", "🔐", "• AES-256 Encryption: All data is encrypted using industry-standard AES-256 encryption\n• Two-Factor Authentication (2FA): Multiple authentication methods including TOTP and email OTP\n• Auto-Lock: Automatic vault locking after inactivity\n• Access Logging: Complete audit trail of all vault activities\n• Secure Key Management: Encryption keys are never stored in plain text"),
                ("Getting Started", "🚀", "1. Registration: Create a new account with username and password\n2. 2FA Setup: Configure two-factor authentication for enhanced security\n3. Adding Items: Use the left panel to add files, folders, or applications\n4. Accessing Items: Double-click items or use the context menu to access them"),
                ("Managing Vault Items", "📁", "• Add Application: Store executable files (.exe) securely\n• Add Folder: Encrypt entire folders and their contents\n• Add File: Secure any type of file with encryption\n• QR Code Scanner: Scan QR codes from camera, files, or clipboard\n• Search: Use the search bar to quickly find items\n• Context Menu: Right-click items for additional options"),
                ("QR Code Scanning", "📱", "• Camera Scan: Use your computer's camera to scan QR codes\n• File Upload: Select an image file containing a QR code\n• Clipboard: Scan QR codes copied to your clipboard\n• Screenshot: Take a screenshot and scan for QR codes\n• External Apps: Open external QR scanner applications\n• Auto-Detection: Automatically detects URLs, 2FA codes, and text\n• Vault Integration: Automatically add scanned data to your vault\n• QR Generation: Create QR codes for text, URLs, WiFi, contacts, and more\n• Save QR Codes: Save generated QR codes as PNG images"),
                ("Search & Filter", "🔍", "• Real-time Search: Type in the search bar for instant results\n• Advanced Search: Use the search dialog for detailed queries\n• QR Code Scanning: Scan QR codes from multiple sources\n• Filter Logs: Filter access logs by status (Success/Failed)\n• Sort Items: Click column headers to sort items"),
                ("Settings", "⚙️", "• Auto-Lock Timeout: Set inactivity timeout (0 to disable)\n• Theme Selection: Choose from multiple UI themes\n• 2FA Requirements: Configure 2FA for different actions\n• Log Level: Adjust logging verbosity"),
                ("Monitoring & Logs", "📊", "• Access Logs: View detailed access history\n• Statistics: Monitor vault usage and item counts\n• Security Events: Track failed access attempts\n• Activity Timeline: See when items were accessed"),
                ("Keyboard Shortcuts", "⌨️", "• Ctrl+Shift+L: Quick lock vault\n• Enter: Login/Confirm actions\n• Double-click: Access selected item\n• Right-click: Context menu\n• Mouse Wheel: Scroll through lists\n• Shift+Mouse Wheel: Horizontal scrolling"),
                ("Mouse Controls", "🖱️", "• Mouse Wheel: Vertical scrolling in all lists and dialogs\n• Shift+Mouse Wheel: Horizontal scrolling\n• Right-click: Context menus for items\n• Double-click: Access items or confirm selections"),
                ("Troubleshooting", "🔧", "• Forgot Password: Contact administrator for password reset\n• 2FA Issues: Use backup codes or email recovery\n• Locked Out: Wait for auto-lock timeout or restart application\n• Performance: Close unnecessary applications to improve speed"),
                ("Support", "📞", "For technical support or security concerns:\n• Check the logs for detailed error information\n• Review the settings for configuration issues\n• Contact your system administrator"),
                ("Security Best Practices", "🔒", "• Use strong, unique passwords\n• Enable 2FA for all accounts\n• Regularly update your password\n• Don't share your 2FA codes\n• Lock the vault when leaving your computer\n• Monitor access logs regularly\n• Keep the application updated"),
                ("Important Notes", "⚠️", "• Never share your master password\n• Keep your 2FA device secure\n• Regular backups are recommended\n• The vault is only as secure as your password\n• Auto-lock helps protect against unauthorized access\n• All access attempts are logged for security"),
                ("Tips", "🎯", "• Use descriptive names for your items\n• Organize items by creating folders\n• Use the search function to find items quickly\n• Set appropriate auto-lock timeout\n• Regularly review and clean up old items\n• Monitor your access patterns in the logs"),
            ]
            section_widgets = {}
            for title, icon, content in help_sections:
                add_section(title, icon)
                text = tk.Text(scrollable_frame, wrap=tk.WORD, font=('Consolas', 10), bg='white', fg='black', height=6, padx=15, pady=8, borderwidth=0, highlightthickness=0)
                text.insert(tk.END, content)
                text.config(state=tk.DISABLED)
                text.pack(fill=tk.X, expand=False, pady=(0, 0))
                section_widgets[title.upper()] = text
            nav_items = [
                ("Overview", "OVERVIEW"),
                ("Security Features", "SECURITY FEATURES"),
                ("Getting Started", "GETTING STARTED"),
                ("Managing Vault Items", "MANAGING VAULT ITEMS"),
                ("QR Code Scanning", "QR CODE SCANNING"),
                ("Search & Filter", "SEARCH AND FILTER"),
                ("Settings", "SETTINGS AND CUSTOMIZATION"),
                ("Monitoring & Logs", "MONITORING AND LOGS"),
                ("Keyboard Shortcuts", "KEYBOARD SHORTCUTS"),
                ("Mouse Controls", "MOUSE CONTROLS"),
                ("Troubleshooting", "TROUBLESHOOTING"),
                ("Support", "SUPPORT"),
                ("Security Best Practices", "SECURITY BEST PRACTICES"),
                ("Important Notes", "IMPORTANT NOTES"),
                ("Tips", "TIPS FOR EFFICIENT USE"),
            ]
            def scroll_to_section(anchor):
                label = section_labels.get(anchor)
                if label:
                    canvas.yview_moveto(label.winfo_y() / max(1, scrollable_frame.winfo_height()))
            for nav, anchor in nav_items:
                btn = ttk.Button(nav_frame, text=nav, style='secondary.TButton', width=20, command=lambda a=anchor: scroll_to_section(a))
                btn.pack(anchor=tk.NW, pady=2, fill=tk.X)
            def filter_help(*args):
                query = search_var.get().strip().lower()
                for title, icon, content in help_sections:
                    widget = section_widgets[title.upper()]
                    if not query or query in content.lower() or query in title.lower():
                        widget.master.pack_configure()
                        widget.pack_configure()
                    else:
                        widget.pack_forget()
            search_var.trace_add('write', filter_help)
            
            # Add control buttons at the bottom
            control_frame = ttk.Frame(help_window)
            control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
            
            # Left side - Window control buttons
            window_controls = ttk.Frame(control_frame)
            window_controls.pack(side=tk.LEFT)
            
            # Minimize button
            def minimize_window():
                help_window.iconify()
            ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Maximize/Restore button
            is_maximized = False
            def toggle_maximize():
                nonlocal is_maximized
                if is_maximized:
                    help_window.geometry("900x700")
                    is_maximized = False
                else:
                    help_window.state('zoomed')
                    is_maximized = True
            ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Right side - Close button
            ttk.Button(control_frame, text="Close", command=help_window.destroy, style='secondary.TButton').pack(side=tk.RIGHT)
            
            # Handle window close event
            def on_help_close():
                help_window.destroy()
            
            help_window.protocol("WM_DELETE_WINDOW", on_help_close)
    def show_search_dialog(self, parent=None, as_tab=False):
        """Show search dialog as popup window"""
        # Create popup window
        search_window = tk.Toplevel(self.root)
        search_window.title("Search - IronLock Vault")
        search_window.geometry("900x700")
        search_window.transient(self.root)
        search_window.grab_set()
        search_window.resizable(True, True)
        
        # Center the window
        search_window.update_idletasks()
        x = (search_window.winfo_screenwidth() // 2) - 450
        y = (search_window.winfo_screenheight() // 2) - 350
        search_window.geometry(f'900x700+{x}+{y}')
        
        # Main container
        main_container = ttk.Frame(search_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Content frame
        frame = ttk.Frame(scrollable_frame, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header frame
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(header_frame, text="🔍 Advanced Search", font=('Arial', 18, 'bold')).pack(side=tk.LEFT)
        stats_btn = ttk.Button(header_frame, text="📊 View Statistics", style='info.TButton')
        stats_btn.pack(side=tk.RIGHT)
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(search_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            search_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                search_window.geometry("900x700")
                is_maximized = False
            else:
                search_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Close button
        ttk.Button(control_frame, text="Close", command=search_window.destroy, style='secondary.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_search_close():
            search_window.destroy()
        
        search_window.protocol("WM_DELETE_WINDOW", on_search_close)

    def create_add_items_panel(self, parent):
        """Create add items panel with improved spacing and tooltips"""
        # Add Application
        btn_app = ttk.Button(
            parent,
            text="📱 Add Application",
            command=lambda: self.add_item_dialog('app'),
            style='success.TButton'
        )
        btn_app.pack(fill=tk.X, pady=6)
        # TODO: Add tooltip: "Add a new application to your vault."
        # Add Folder
        btn_folder = ttk.Button(
            parent,
            text="📁 Add Folder",
            command=lambda: self.add_item_dialog('folder'),
            style='success.TButton'
        )
        btn_folder.pack(fill=tk.X, pady=6)
        # TODO: Add tooltip: "Add a new folder to your vault."
        # Add File
        btn_file = ttk.Button(
            parent,
            text="📄 Add File",
            command=lambda: self.add_item_dialog('file'),
            style='success.TButton'
        )
        btn_file.pack(fill=tk.X, pady=6)
        # TODO: Add tooltip: "Add a new file to your vault."
        # Separator
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        # Quick stats
        stats_frame = ttk.LabelFrame(parent, text="Vault Stats", padding=10)
        stats_frame.pack(fill=tk.X, pady=5)
        self.stats_labels = {
            'total': ttk.Label(stats_frame, text="Total Items: 0", font=("Arial", 10, "bold")),
            'apps': ttk.Label(stats_frame, text="Applications: 0"),
            'folders': ttk.Label(stats_frame, text="Folders: 0"),
            'files': ttk.Label(stats_frame, text="Files: 0")
        }
        for label in self.stats_labels.values():
            label.pack(anchor=tk.W, pady=2)

    def create_vault_items_panel(self, parent):
        """Create vault items display panel with improved section header and spacing"""
        # Section header
        header = ttk.Label(parent, text="🗄️ Your Vault Items", font=("Arial", 16, "bold"))
        header.pack(anchor=tk.W, pady=(0, 10))
        # Search frame
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").pack(side=LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        ttk.Button(
            search_frame,
            text="Clear",
            command=lambda: self.search_var.set(""),
            style='secondary.TButton'
        ).pack(side=RIGHT)
        
        # Items frame with enhanced scrolling
        items_container = ttk.Frame(parent)
        items_container.pack(fill=BOTH, expand=True)
        
        # Create a frame for the treeview and scrollbars
        tree_frame = ttk.Frame(items_container)
        tree_frame.pack(fill=BOTH, expand=True)
        
        # Treeview for items
        columns = ('Name', 'Type', 'Version', 'Integrity', 'Added', 'Last Accessed', 'Access Count', 'Original Location')
        self.items_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=15)
        
        # Configure tree column for checkboxes
        self.items_tree.heading('#0', text='Select')
        self.items_tree.column('#0', width=40, minwidth=30, anchor='center')
        self.items_tree.heading('Name', text='Name')
        self.items_tree.heading('Type', text='Type')
        self.items_tree.heading('Version', text='Version')
        self.items_tree.heading('Integrity', text='Integrity')
        self.items_tree.heading('Added', text='Added')
        self.items_tree.heading('Last Accessed', text='Last Accessed')
        self.items_tree.heading('Access Count', text='Access Count')
        self.items_tree.heading('Original Location', text='Original Location')
        self.items_tree.column('Name', width=200, minwidth=150)
        self.items_tree.column('Type', width=100, minwidth=80)
        self.items_tree.column('Version', width=70, minwidth=50)
        self.items_tree.column('Integrity', width=90, minwidth=70)
        self.items_tree.column('Added', width=150, minwidth=120)
        self.items_tree.column('Last Accessed', width=150, minwidth=120)
        self.items_tree.column('Access Count', width=100, minwidth=80)
        self.items_tree.column('Original Location', width=250, minwidth=150)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.items_tree.xview)
        self.items_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.items_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.create_context_menu()
        
        # Bind events
        self.items_tree.bind('<Double-1>', self.on_item_double_click)
        self.items_tree.bind('<Button-3>', self.show_context_menu)
        
        # Enhanced keyboard navigation
        self.items_tree.bind('<Up>', self.on_tree_navigate)
        self.items_tree.bind('<Down>', self.on_tree_navigate)
        self.items_tree.bind('<Home>', self.on_tree_navigate)
        self.items_tree.bind('<End>', self.on_tree_navigate)
        self.items_tree.bind('<Page_Up>', self.on_tree_navigate)
        self.items_tree.bind('<Page_Down>', self.on_tree_navigate)
        
        # Mouse wheel scrolling
        self.items_tree.bind('<MouseWheel>', self.on_mouse_wheel)
        self.items_tree.bind('<Shift-MouseWheel>', self.on_shift_mouse_wheel)
        
        # Keyboard shortcuts
        self.items_tree.bind('<Control-a>', self.select_all_items)
        self.items_tree.bind('<Control-A>', self.select_all_items)
        self.items_tree.bind('<Control-u>', self.unselect_all_items)
        self.items_tree.bind('<Control-U>', self.unselect_all_items)
        # Bind click event for checkbox toggling
        self.items_tree.bind('<Button-1>', self.on_treeview_click)
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling"""
        self.items_tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    
    def on_shift_mouse_wheel(self, event):
        """Handle shift + mouse wheel for horizontal scrolling"""
        self.items_tree.xview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    
    def on_tree_navigate(self, event):
        """Handle keyboard navigation in treeview"""
        if event.keysym == 'Up':
            self.items_tree.yview_scroll(-1, "units")
        elif event.keysym == 'Down':
            self.items_tree.yview_scroll(1, "units")
        elif event.keysym == 'Home':
            self.items_tree.yview_moveto(0)
        elif event.keysym == 'End':
            self.items_tree.yview_moveto(1)
        elif event.keysym == 'Page_Up':
            self.items_tree.yview_scroll(-10, "units")
        elif event.keysym == 'Page_Down':
            self.items_tree.yview_scroll(10, "units")
        return "break"
    
    def create_context_menu(self):
        """Create context menu for items"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📋 Select All", command=self.select_all_items)
        self.context_menu.add_command(label="❌ Unselect All", command=self.unselect_all_items)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔓 Access Item", command=self.access_selected_item)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="ℹ️ Item Info", command=self.show_item_info)
        self.context_menu.add_command(label="🗑️ Remove Item", command=self.remove_selected_item)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🛡️ Verify Integrity", command=self.verify_integrity_selected_item)
        self.context_menu.add_command(label="🕓 Show Versions", command=self.show_versions_selected_item)
        self.context_menu.add_command(label="🗑️ Secure Delete (Original)", command=self.secure_delete_selected_item)
    
    def show_context_menu(self, event):
        """Show context menu with dynamic options based on selection"""
        # Clear existing menu items
        self.context_menu.delete(0, tk.END)
        
        # Get current selection
        selection = self.items_tree.selection()
        item_count = len(selection)
        
        # Add Select All and Unselect All options
        self.context_menu.add_command(label="📋 Select All", command=self.select_all_items)
        self.context_menu.add_command(label="❌ Unselect All", command=self.unselect_all_items)
        self.context_menu.add_separator()
        
        if item_count == 0:
            # No selection - only show Select All and Unselect All
            pass
        elif item_count == 1:
            # Single item selection
            self.context_menu.add_command(label="🔓 Access Item", command=self.access_selected_item)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="ℹ️ Item Info", command=self.show_item_info)
            self.context_menu.add_command(label="🗑️ Remove Item", command=self.remove_selected_item)
            self.context_menu.add_separator()
            self.context_menu.add_command(label="🛡️ Verify Integrity", command=self.verify_integrity_selected_item)
            self.context_menu.add_command(label="🕓 Show Versions", command=self.show_versions_selected_item)
            self.context_menu.add_command(label="🗑️ Secure Delete (Original)", command=self.secure_delete_selected_item)
        else:
            # Multiple items selected
            self.context_menu.add_command(label=f"🔓 Access All ({item_count} items)", command=self.access_all_selected_items)
            self.context_menu.add_separator()
            self.context_menu.add_command(label=f"🗑️ Remove All ({item_count} items)", command=self.remove_all_selected_items)
        
        # Show the menu
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def create_status_bar(self, parent):
        """Create status bar"""
        self.status_bar = ttk.Frame(parent)
        self.status_bar.pack(fill=X, side=BOTTOM, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side=LEFT)
        
        # Time display
        self.time_label = ttk.Label(self.status_bar, text="")
        self.time_label.pack(side=RIGHT)
        
        self.update_time()
    
    def update_time(self):
        """Update time display"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=current_time)
            self.root.after(1000, self.update_time)
        except tk.TclError:
            # Widget has been destroyed, stop updating
            pass
        except Exception as e:
            # Other errors, stop updating
            pass
    
    def add_item_dialog(self, item_type):
        """Show add item dialog"""
        if item_type == 'app':
            file_path = filedialog.askopenfilename(
                title="Select Application",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
        elif item_type == 'folder':
            file_path = filedialog.askdirectory(title="Select Folder")
        else:  # file
            file_path = filedialog.askopenfilename(
                title="Select File",
                filetypes=[("All files", "*.*")]
            )
        
        if file_path:
            # Show 2FA verification before adding
            self.verify_otp_for_sensitive_action(lambda: self.add_item_to_vault(file_path, item_type))
    
    def add_item_to_vault(self, file_path, item_type):
        """Add item to vault after 2FA verification"""
        if self.current_user is None or 'username' not in self.current_user:
            messagebox.showerror("Error", "No user is currently logged in.")
            return
        success, message = self.vault_manager.add_item(file_path, item_type, self.current_user['username'])
        
        if success:
            self.status_label.config(text=message)
            self.refresh_vault_items()
            
            # Check if the message indicates the original file couldn't be removed
            if "could not be removed" in message.lower():
                # Show a more detailed dialog with options
                self.show_file_removal_warning(file_path, message)
            else:
                messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    def show_file_removal_warning(self, file_path, success_message):
        """Show warning when original file couldn't be removed"""
        warning_window = tk.Toplevel(self.root)
        warning_window.title("File Removal Warning")
        warning_window.geometry("500x300")
        warning_window.transient(self.root)
        warning_window.grab_set()
        
        # Center window
        warning_window.update_idletasks()
        x = (warning_window.winfo_screenwidth() // 2) - 250
        y = (warning_window.winfo_screenheight() // 2) - 150
        warning_window.geometry(f'500x300+{x}+{y}')
        
        # Main frame
        main_frame = ttk.Frame(warning_window, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Warning icon and title
        ttk.Label(main_frame, text="⚠️ File Added to Vault", font=('Arial', 16, 'bold')).pack(pady=(0, 10))
        
        # Success message
        ttk.Label(main_frame, text=success_message, font=('Arial', 11), wraplength=450).pack(pady=(0, 15))
        
        # Warning about original file
        warning_text = f"The original file still exists at:\n{file_path}\n\nFor security, you should manually delete this file."
        ttk.Label(main_frame, text=warning_text, font=('Arial', 10), foreground='orange', wraplength=450).pack(pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=X, pady=(0, 10))
        
        def open_file_location():
            """Open the folder containing the original file"""
            try:
                import subprocess
                import platform
                file_dir = str(Path(file_path).parent)
                
                if platform.system() == 'Windows':
                    subprocess.run(['explorer', file_dir])
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', file_dir])
                else:  # Linux
                    subprocess.run(['xdg-open', file_dir])
            except Exception as e:
                self.logger.log_error(f"Failed to open file location: {str(e)}")
                messagebox.showerror("Error", f"Failed to open file location: {str(e)}")
        
        def try_remove_original():
            """Attempt to remove the original file"""
            success, message = self.vault_manager.try_remove_original_file(file_path)
            
            if success:
                messagebox.showinfo("Success", message)
                warning_window.destroy()
            else:
                messagebox.showerror("Error", message)
        
        # Button to open file location
        ttk.Button(buttons_frame, text="📁 Open File Location", 
                  command=open_file_location, style='info.TButton').pack(side=LEFT, padx=(0, 10))
        
        # Button to try removing the file
        ttk.Button(buttons_frame, text="🗑️ Remove Original File", 
                  command=try_remove_original, style='warning.TButton').pack(side=LEFT, padx=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(10, 0))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            warning_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                warning_window.geometry("500x300")
                is_maximized = False
            else:
                warning_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Close button
        ttk.Button(control_frame, text="Close", 
                  command=warning_window.destroy, style='danger.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_warning_close():
            warning_window.destroy()
        
        warning_window.protocol("WM_DELETE_WINDOW", on_warning_close)
    
    def verify_otp_for_sensitive_action(self, on_success):
        """Show dialog to choose and verify Email/SMS OTP for sensitive actions"""
        otp_window = tk.Toplevel(self.root)
        otp_window.title("OTP Verification Required")
        otp_window.geometry("450x500")
        otp_window.transient(self.root)
        otp_window.grab_set()
        otp_window.resizable(True, True)
        
        # Center window
        otp_window.update_idletasks()
        x = (otp_window.winfo_screenwidth() // 2) - 225
        y = (otp_window.winfo_screenheight() // 2) - 250
        otp_window.geometry(f'450x500+{x}+{y}')
        
        # Main container with scrollbar
        main_container = ttk.Frame(otp_window)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Content frame
        frame = ttk.Frame(scrollable_frame, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(frame, text="🔐 OTP Verification Required", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        ttk.Label(frame, text="To proceed with this action, you need to verify your identity using a one-time password.", 
                 font=('Arial', 11), wraplength=400).pack(pady=(0, 15))
        ttk.Label(frame, text="Choose a method to receive your OTP code:", 
                 font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Determine available methods
        has_email = self.auth_manager.current_user and self.auth_manager.current_user.get('email')
        has_mobile = self.auth_manager.current_user and self.auth_manager.current_user.get('mobile_number')
        
        if not has_email and not has_mobile:
            ttk.Label(frame, text="❌ No email or mobile number configured for OTP delivery.", 
                     font=('Arial', 10), foreground='red').pack(pady=(0, 15))
            ttk.Label(frame, text="Please configure your email or mobile number in your profile settings first.", 
                     font=('Arial', 9), wraplength=400).pack(pady=(0, 15))
            ttk.Button(frame, text="Close", command=otp_window.destroy, style='danger.TButton').pack(pady=(10, 0))
            return
        
        method_var = tk.StringVar(value='Email' if has_email else 'SMS')
        
        # Method selection frame
        method_frame = ttk.LabelFrame(frame, text="OTP Delivery Method", padding=15)
        method_frame.pack(fill=X, pady=(0, 15))
        
        # Method selection
        if has_email:
            email_radio = ttk.Radiobutton(method_frame, text=f"📧 Email OTP", variable=method_var, value='Email')
            email_radio.pack(anchor=W, pady=2)
            ttk.Label(method_frame, text=f"   Send code to: {self.auth_manager.current_user.get('email')}", 
                     font=('Arial', 9), foreground='gray').pack(anchor=W, padx=(20, 0))
        
        if has_mobile:
            sms_radio = ttk.Radiobutton(method_frame, text=f"📱 SMS OTP", variable=method_var, value='SMS')
            sms_radio.pack(anchor=W, pady=2)
            ttk.Label(method_frame, text=f"   Send code to: {self.auth_manager.current_user.get('mobile_number')}", 
                     font=('Arial', 9), foreground='gray').pack(anchor=W, padx=(20, 0))
        
        # Send OTP button
        send_btn = ttk.Button(frame, text="📤 Send OTP Code", style='info.TButton')
        send_btn.pack(pady=(10, 15))
        
        # OTP verification frame (hidden until sent)
        verify_frame = ttk.LabelFrame(frame, text="Enter OTP Code", padding=15)
        otp_label = ttk.Label(verify_frame, text="Enter the 6-digit OTP code sent to your selected method:", 
                             font=('Arial', 10), wraplength=350)
        otp_entry = ttk.Entry(verify_frame, font=('Arial', 14), justify=CENTER, width=15)
        verify_btn = ttk.Button(verify_frame, text="✅ Verify OTP", style='success.TButton')
        resend_btn = ttk.Button(verify_frame, text="🔄 Resend OTP", style='secondary.TButton')
        
        def send_otp():
            method = method_var.get()
            if method == 'Email':
                success, msg = self.auth_manager.generate_email_otp()
            else:
                success, msg = self.auth_manager.generate_mobile_otp()
            if success:
                messagebox.showinfo("OTP Sent", msg)
                verify_frame.pack(fill=X, pady=(0, 15))
                otp_label.pack(pady=(0, 10))
                otp_entry.pack(pady=(0, 15))
                verify_btn.pack(pady=(0, 5))
                resend_btn.pack(pady=(0, 5))
                otp_entry.focus()
                # Scroll to show the verification frame
                canvas.yview_moveto(1)
            else:
                messagebox.showerror("Error", msg)
        
        def verify_otp():
            code = otp_entry.get().strip()
            method = method_var.get()
            if not code:
                messagebox.showerror("Error", "Please enter the OTP code")
                return
            if len(code) != 6:
                messagebox.showerror("Error", "OTP code must be 6 digits")
                return
            if method == 'Email':
                valid = self.auth_manager.verify_email_otp(code)
            else:
                valid = self.auth_manager.verify_mobile_otp(code)
            if valid:
                otp_window.destroy()
                on_success()
            else:
                messagebox.showerror("Verification Failed", "Invalid or expired OTP code")
                otp_entry.delete(0, tk.END)
        
        send_btn.config(command=send_otp)
        verify_btn.config(command=verify_otp)
        resend_btn.config(command=send_otp)
        otp_entry.bind('<Return>', lambda e: verify_otp())
        
        # Bottom buttons frame
        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(fill=X, pady=(15, 0))
        
        ttk.Button(bottom_frame, text="❌ Cancel", command=otp_window.destroy, 
                  style='danger.TButton').pack(side=RIGHT)
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(otp_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            otp_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                otp_window.geometry("450x500")
                is_maximized = False
            else:
                otp_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Unbind mousewheel when window closes
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            otp_window.destroy()
        
        otp_window.protocol("WM_DELETE_WINDOW", on_closing)

    def verify_2fa_for_password_change(self, current_password, new_password):
        """Use OTP for password change verification"""
        def on_success():
            self.perform_password_change(current_password, new_password)
        self.verify_otp_for_sensitive_action(on_success)

    def verify_2fa_for_profile_update(self, new_email, new_mobile, new_fullname, new_org):
        """Use OTP for profile update verification"""
        def on_success():
            self.perform_profile_update(new_email, new_mobile, new_fullname, new_org)
        self.verify_otp_for_sensitive_action(on_success)
    
    def show_2fa_setup_prompt(self, action_callback):
        """Show 2FA setup prompt for users without 2FA"""
        setup_window = tk.Toplevel(self.root)
        setup_window.title("2FA Setup Recommended")
        setup_window.geometry("450x300")
        setup_window.transient(self.root)
        setup_window.grab_set()
        
        # Center window
        setup_window.update_idletasks()
        x = (setup_window.winfo_screenwidth() // 2) - 225
        y = (setup_window.winfo_screenheight() // 2) - 150
        setup_window.geometry(f'450x300+{x}+{y}')
        
        frame = ttk.Frame(setup_window, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(
            frame, 
            text="🔐 Two-Factor Authentication", 
            font=('Arial', 16, 'bold')
        ).pack(pady=(0, 15))
        
        ttk.Label(
            frame, 
            text="For enhanced security, we recommend setting up two-factor authentication before performing sensitive actions.",
            font=('Arial', 11),
            wraplength=400
        ).pack(pady=(0, 20))
        
        # Options frame
        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            options_frame,
            text="Choose an option:",
            font=('Arial', 12, 'bold')
        ).pack(pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill=X)
        
        def setup_2fa():
            setup_window.destroy()
            self.show_2fa_setup_dialog()
        
        def skip_and_continue():
            setup_window.destroy()
            action_callback()
        
        ttk.Button(
            buttons_frame,
            text="🔐 Set Up 2FA Now",
            command=setup_2fa,
            style='success.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            buttons_frame,
            text="⏭️ Skip for Now",
            command=skip_and_continue,
            style='secondary.TButton'
        ).pack(side=LEFT)
        
        ttk.Button(
            buttons_frame,
            text="❌ Cancel",
            command=setup_window.destroy,
            style='danger.TButton'
        ).pack(side=RIGHT)
        
        # Add control buttons at the bottom
        control_frame = ttk.Frame(setup_window)
        control_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            setup_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                setup_window.geometry("450x300")
                is_maximized = False
            else:
                setup_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, 
                  style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Handle window close event
        def on_setup_close():
            setup_window.destroy()
        
        setup_window.protocol("WM_DELETE_WINDOW", on_setup_close)
    
    def show_2fa_setup_dialog(self):
        """Show 2FA setup dialog for existing users"""
        setup_window = tk.Toplevel(self.root)
        setup_window.title("Set Up Two-Factor Authentication")
        setup_window.geometry("500x600")
        setup_window.transient(self.root)
        setup_window.grab_set()
        
        # Center window
        setup_window.update_idletasks()
        x = (setup_window.winfo_screenwidth() // 2) - 250
        y = (setup_window.winfo_screenheight() // 2) - 300
        setup_window.geometry(f'500x600+{x}+{y}')
        
        frame = ttk.Frame(setup_window, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(
            frame, 
            text="🔐 Set Up Two-Factor Authentication", 
            font=('Arial', 16, 'bold')
        ).pack(pady=(0, 20))
        
        ttk.Label(
            frame, 
            text="Follow these steps to set up TOTP (Google Authenticator):",
            font=('Arial', 11)
        ).pack(pady=(0, 20))
        
        # Instructions
        instructions = [
            "1. Download an authenticator app:",
            "   • Google Authenticator",
            "   • Authy",
            "   • Microsoft Authenticator",
            "   • Any TOTP-compatible app",
            "",
            "2. Click 'Show QR Code' below",
            "3. Scan the QR code with your app",
            "4. Enter the 6-digit code to verify",
            "",
            "This will add an extra layer of security to your vault."
        ]
        
        for instruction in instructions:
            if instruction.startswith("1.") or instruction.startswith("2.") or instruction.startswith("3.") or instruction.startswith("4."):
                ttk.Label(
                    frame,
                    text=instruction,
                    font=('Arial', 11, 'bold')
                ).pack(anchor=W, pady=2)
            elif instruction.startswith("   •"):
                ttk.Label(
                    frame,
                    text=instruction,
                    font=('Arial', 10)
                ).pack(anchor=W, pady=1, padx=(20, 0))
            else:
                ttk.Label(
                    frame,
                    text=instruction,
                    font=('Arial', 10)
                ).pack(anchor=W, pady=2)
        
        # Buttons frame
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(pady=30)
        
        def show_qr():
            setup_window.destroy()
            self.show_qr_code()
        
        ttk.Button(
            buttons_frame,
            text="📱 Show QR Code",
            command=show_qr,
            style='info.TButton'
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            buttons_frame,
            text="❌ Cancel",
            command=setup_window.destroy,
            style='secondary.TButton'
        ).pack(side=LEFT)
        
        # Control buttons frame
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=X, pady=(10, 0))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            setup_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                setup_window.geometry("500x600")
                is_maximized = False
            else:
                setup_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Handle window close event
        def on_setup_close():
            setup_window.destroy()
        
        setup_window.protocol("WM_DELETE_WINDOW", on_setup_close)
    
    def refresh_vault_items(self):
        """Refresh vault items display"""
        # Clear existing items
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Get items from vault
        items = self.vault_manager.get_vault_items(self.current_user['username'])
        
        # Add items to tree
        item_id_map = {}  # Map from item DB id to treeview item id
        for item in items:
            # Format dates
            added_date = item['added_date'][:19] if item['added_date'] else 'N/A'
            last_accessed = item['last_accessed'][:19] if item['last_accessed'] else 'Never'
            version = item.get('version', 1)
            integrity = item.get('integrity', 'Not Checked')
            
            # Get type icon
            type_icons = {'app': '📱', 'folder': '📁', 'file': '📄'}
            type_display = f"{type_icons.get(item['item_type'], '❓')} {item['item_type'].title()}"
            
            # Checkbox image
            checkbox_img = self.checkbox_checked if str(item['id']) in self.selected_items else self.checkbox_unchecked
            tree_id = self.items_tree.insert('', 'end', text='', image=checkbox_img, values=(item['name'], type_display, version, integrity, added_date, last_accessed, item['access_count'], item['original_path']), tags=(item['id'],))
            item_id_map[str(item['id'])] = tree_id
        
        # Re-apply selection to match self.selected_items
        self.items_tree.selection_remove(self.items_tree.selection())
        for item_id in self.selected_items:
            tree_id = item_id_map.get(item_id)
            if tree_id:
                self.items_tree.selection_add(tree_id)
        
        # Update stats
        self.update_stats(items)
    
    def update_stats(self, items):
        """Update vault statistics"""
        if not hasattr(self, 'stats_labels') or not isinstance(self.stats_labels, dict):
            return
        total = len(items)
        apps = len([i for i in items if i['item_type'] == 'app'])
        folders = len([i for i in items if i['item_type'] == 'folder'])
        files = len([i for i in items if i['item_type'] == 'file'])
        self.stats_labels['total'].config(text=f"Total Items: {total}")
        self.stats_labels['apps'].config(text=f"Applications: {apps}")
        self.stats_labels['folders'].config(text=f"Folders: {folders}")
        self.stats_labels['files'].config(text=f"Files: {files}")
    
    def on_search_change(self, *args):
        """Handle search input change with enhanced functionality"""
        query = self.search_var.get().strip()
        
        # Get search suggestions if query is long enough
        if len(query) >= 2:
            suggestions = self.vault_manager.get_search_suggestions(query, self.current_user['username'])
            # Could implement suggestion dropdown here
        
        if query:
            # Use enhanced search with fuzzy matching
            items = self.vault_manager.search_items(
                query, 
                self.current_user['username'],
                search_type='fuzzy',  # Use fuzzy search for better results
                limit=100  # Limit results for performance
            )
        else:
            items = self.vault_manager.get_vault_items(self.current_user['username'])
        
        # Update display
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Add items to tree with proper checkbox handling
        item_id_map = {}  # Map from item DB id to treeview item id
        for item in items:
            # Format dates
            added_date = item['added_date'][:19] if item['added_date'] else 'N/A'
            last_accessed = item['last_accessed'][:19] if item['last_accessed'] else 'Never'
            version = item.get('version', 1)
            integrity = item.get('integrity', 'Not Checked')
            
            # Get type icon
            type_icons = {'app': '📱', 'folder': '📁', 'file': '📄'}
            type_display = f"{type_icons.get(item['item_type'], '❓')} {item['item_type'].title()}"
            
            # Checkbox image
            checkbox_img = self.checkbox_checked if str(item['id']) in self.selected_items else self.checkbox_unchecked
            tree_id = self.items_tree.insert('', 'end', text='', image=checkbox_img, values=(item['name'], type_display, version, integrity, added_date, last_accessed, item['access_count'], item['original_path']), tags=(item['id'],))
            item_id_map[str(item['id'])] = tree_id
        
        # Re-apply selection to match self.selected_items
        self.items_tree.selection_remove(self.items_tree.selection())
        for item_id in self.selected_items:
            tree_id = item_id_map.get(item_id)
            if tree_id:
                self.items_tree.selection_add(tree_id)
        
        # Update status with search results count
        if query:
            self.status_label.config(text=f"Search results: {len(items)} items found for '{query}'")
        else:
            self.status_label.config(text="Ready")
    
    def on_item_double_click(self, event):
        """Handle item double click"""
        self.access_selected_item()
    
    def access_selected_item(self):
        """Access selected item with 2FA"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to access")
            return
        
        item_id = self.items_tree.item(selection[0])['tags'][0]
        
        # Verify 2FA before access
        self.verify_otp_for_sensitive_action(lambda: self.access_item(item_id))
    
    def access_item(self, item_id):
        """Access item after 2FA verification"""
        success, message = self.vault_manager.access_item(item_id, self.current_user['username'])
        
        if success:
            self.status_label.config(text=message)
            self.refresh_vault_items()  # Update access count
        else:
            messagebox.showerror("Access Failed", message)
    
    def remove_selected_item(self):
        """Remove selected item"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to remove")
            return
        
        item_name = self.items_tree.item(selection[0])['values'][0]
        
        if messagebox.askyesno("Confirm Removal", f"Remove '{item_name}' from vault?"):
            item_id = self.items_tree.item(selection[0])['tags'][0]
            success, message = self.vault_manager.remove_item(item_id, self.current_user['username'])
            
            if success:
                self.status_label.config(text=message)
                self.refresh_vault_items()
                messagebox.showinfo("Success", message)
            else:
                messagebox.showerror("Error", message)
    
    def show_item_info(self):
        """Show item information in a scrollable dialog"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item")
            return
        
        values = self.items_tree.item(selection[0])['values']
        item_id = self.items_tree.item(selection[0])['tags'][0]
        
        # Get detailed item info from vault manager
        item_details = self.vault_manager.get_item_details(item_id, self.current_user['username'])
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Item Information")
        info_window.geometry("500x400")
        info_window.transient(self.root)
        info_window.resizable(True, True)
        
        # Center window
        info_window.update_idletasks()
        x = (info_window.winfo_screenwidth() // 2) - 250
        y = (info_window.winfo_screenheight() // 2) - 200
        info_window.geometry(f'500x400+{x}+{y}')
        
        frame = ttk.Frame(info_window, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        ttk.Label(frame, text="Item Information", font=('Arial', 14, 'bold')).pack(pady=(0, 15))
        
        # Create scrollable text area
        text_container = ttk.Frame(frame)
        text_container.pack(fill=BOTH, expand=True)
        
        # Text widget with scrollbar
        text_widget = tk.Text(text_container, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_container, orient=VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Mouse wheel scrolling
        def on_mouse_wheel(event):
            text_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
        text_widget.bind('<MouseWheel>', on_mouse_wheel)
        
        # Format detailed information
        info_text = f"""
📋 ITEM DETAILS
{'='*50}

📝 Basic Information:
  • Name: {values[0]}
  • Type: {values[1]}
  • Version: {values[2]}
  • Integrity: {values[3]}
  • Added: {values[4]}
  • Last Accessed: {values[5]}
  • Access Count: {values[6]}

🔍 Detailed Information:
  • Item ID: {item_id}
  • Original Path: {item_details.get('original_path', 'N/A')}
  • Encrypted Path: {item_details.get('encrypted_path', 'N/A')}
  • File Size: {item_details.get('file_size', 'N/A')}
  • Encryption Method: {item_details.get('encryption_method', 'AES-256')}
  • Created By: {item_details.get('created_by', self.current_user)}
  • Created Date: {item_details.get('created_date', 'N/A')}

🔐 Security Information:
  • Encryption Status: {'✅ Encrypted' if item_details.get('is_encrypted', True) else '❌ Not Encrypted'}
  • Access Permissions: {item_details.get('permissions', 'Owner Only')}
  • Last Modified: {item_details.get('last_modified', 'N/A')}

📊 Usage Statistics:
  • Total Accesses: {values[6]}
  • First Access: {item_details.get('first_access', 'Never')}
  • Average Access Time: {item_details.get('avg_access_time', 'N/A')}
  • Last Access Duration: {item_details.get('last_access_duration', 'N/A')}

💾 Storage Information:
  • Storage Location: {item_details.get('storage_location', 'Local Vault')}
  • Backup Status: {item_details.get('backup_status', 'Not Backed Up')}
  • Compression: {item_details.get('compression', 'None')}
"""
        
        text_widget.insert(tk.END, info_text)
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        # Control buttons frame
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill=X, pady=(10, 0))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            info_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                info_window.geometry("500x400")
                is_maximized = False
            else:
                info_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Close button
        ttk.Button(control_frame, text="Close", command=info_window.destroy, 
                  style='primary.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_info_close():
            info_window.destroy()
        
        info_window.protocol("WM_DELETE_WINDOW", on_info_close)
    
    def select_all_items(self, event=None):
        """Select all items in the vault (checkboxes and selection)"""
        all_items = self.items_tree.get_children()
        if not all_items:
            messagebox.showinfo("No Items", "No items in vault to select")
            return
        # Select all in Treeview
        for item in all_items:
            self.items_tree.selection_add(item)
        # Select all checkboxes
        self.selected_items = set()
        for item in all_items:
            item_tags = self.items_tree.item(item, 'tags')
            if item_tags:
                self.selected_items.add(str(item_tags[0]))
        self.refresh_vault_items()
        selected_count = len(self.selected_items)
        self.status_label.config(text=f"Selected {selected_count} items")
        self.logger.log_info(f"User selected all {selected_count} items")
        return "break"  # Prevent default behavior for keyboard shortcuts
    
    def unselect_all_items(self, event=None):
        """Unselect all items in the vault (checkboxes and selection)"""
        # Clear Treeview selection
        self.items_tree.selection_remove(self.items_tree.selection())
        # Clear checkbox selection
        self.selected_items.clear()
        self.refresh_vault_items()
        self.status_label.config(text="No items selected")
        self.logger.log_info("User unselected all items")
        return "break"  # Prevent default behavior for keyboard shortcuts
    

    
    def access_all_selected_items(self):
        """Access all selected items with 2FA verification"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select items to access")
            return
        
        if len(selection) == 1:
            # Single item - use existing method
            self.access_selected_item()
            return
        
        # Multiple items - show confirmation
        item_count = len(selection)
        if not messagebox.askyesno("Confirm Bulk Access", 
                                 f"Access all {item_count} selected items?\n\nThis will require 2FA verification."):
            return
        
        # Verify 2FA before bulk access
        self.verify_otp_for_sensitive_action(lambda: self.perform_bulk_access(selection))
    
    def perform_bulk_access(self, selected_items):
        """Perform bulk access operation after 2FA verification"""
        success_count = 0
        failed_items = []
        
        for item in selected_items:
            item_id = self.items_tree.item(item)['tags'][0]
            success, message = self.vault_manager.access_item(item_id, self.current_user['username'])
            
            if success:
                success_count += 1
            else:
                item_name = self.items_tree.item(item)['values'][0]
                failed_items.append(item_name)
        
        # Show results
        if success_count == len(selected_items):
            messagebox.showinfo("Success", f"Successfully accessed all {success_count} items")
        elif success_count > 0:
            failed_list = "\n".join(failed_items)
            messagebox.showwarning("Partial Success", 
                                f"Successfully accessed {success_count} items.\n\nFailed to access:\n{failed_list}")
        else:
            failed_list = "\n".join(failed_items)
            messagebox.showerror("Access Failed", f"Failed to access any items:\n{failed_list}")
        
        # Refresh the display
        self.refresh_vault_items()
        self.status_label.config(text=f"Bulk access completed: {success_count}/{len(selected_items)} successful")
    
    def remove_all_selected_items(self):
        """Remove all selected items with confirmation"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select items to remove")
            return
        
        if len(selection) == 1:
            # Single item - use existing method
            self.remove_selected_item()
            return
        
        # Multiple items - show confirmation
        item_count = len(selection)
        item_names = [self.items_tree.item(item)['values'][0] for item in selection]
        item_list = "\n".join(f"• {name}" for name in item_names[:10])  # Show first 10
        if len(item_names) > 10:
            item_list += f"\n... and {len(item_names) - 10} more items"
        
        if not messagebox.askyesno("Confirm Bulk Removal", 
                                 f"Remove all {item_count} selected items?\n\nThis action cannot be undone.\n\nItems to remove:\n{item_list}"):
            return
        
        # Verify 2FA before bulk removal
        self.verify_otp_for_sensitive_action(lambda: self.perform_bulk_removal(selection))
    
    def perform_bulk_removal(self, selected_items):
        """Perform bulk removal operation after 2FA verification"""
        success_count = 0
        failed_items = []
        
        for item in selected_items:
            item_id = self.items_tree.item(item)['tags'][0]
            success, message = self.vault_manager.remove_item(item_id, self.current_user['username'])
            
            if success:
                success_count += 1
            else:
                item_name = self.items_tree.item(item)['values'][0]
                failed_items.append(item_name)
        
        # Show results
        if success_count == len(selected_items):
            messagebox.showinfo("Success", f"Successfully removed all {success_count} items")
        elif success_count > 0:
            failed_list = "\n".join(failed_items)
            messagebox.showwarning("Partial Success", 
                                f"Successfully removed {success_count} items.\n\nFailed to remove:\n{failed_list}")
        else:
            failed_list = "\n".join(failed_items)
            messagebox.showerror("Removal Failed", f"Failed to remove any items:\n{failed_list}")
        
        # Refresh the display
        self.refresh_vault_items()
        self.status_label.config(text=f"Bulk removal completed: {success_count}/{len(selected_items)} successful")
    
    def show_search_dialog(self):
        """Show advanced search dialog with modern UI and enhanced features"""
        search_window = tk.Toplevel(self.root)
        search_window.title("🔍 Advanced Search - IronLock Vault")
        search_window.geometry("1000x700")
        search_window.transient(self.root)
        search_window.resizable(True, True)
        
        # Center window
        search_window.update_idletasks()
        x = (search_window.winfo_screenwidth() // 2) - 500
        y = (search_window.winfo_screenheight() // 2) - 350
        search_window.geometry(f'1000x700+{x}+{y}')
        
        # Main container with scrollbar
        main_container = ttk.Frame(search_window)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Create canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel scrolling for canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Content frame
        frame = ttk.Frame(scrollable_frame, padding=20)
        frame.pack(fill=BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(header_frame, text="🔍 Advanced Search", font=('Arial', 18, 'bold')).pack(side=LEFT)
        
        # Statistics button
        stats_btn = ttk.Button(header_frame, text="📊 View Statistics", style='info.TButton')
        stats_btn.pack(side=RIGHT)
        
        # Search controls frame
        search_controls = ttk.LabelFrame(frame, text="Search Criteria", padding=15)
        search_controls.pack(fill=X, pady=(0, 20))
        
        # First row - Basic search
        basic_frame = ttk.Frame(search_controls)
        basic_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(basic_frame, text="Search Query:").pack(side=LEFT, padx=(0, 10))
        search_entry = ttk.Entry(basic_frame, font=('Arial', 12), width=30)
        search_entry.pack(side=LEFT, padx=(0, 10))
        
        # Search type dropdown
        search_type_var = tk.StringVar(value='name')
        ttk.Label(basic_frame, text="Search in:").pack(side=LEFT, padx=(10, 5))
        search_type_combo = ttk.Combobox(basic_frame, textvariable=search_type_var, 
                                        values=['name', 'path', 'all', 'fuzzy'], 
                                        state='readonly', width=10)
        search_type_combo.pack(side=LEFT, padx=(0, 10))
        
        # Quick search button
        quick_search_btn = ttk.Button(basic_frame, text="🔍 Quick Search", style='success.TButton')
        quick_search_btn.pack(side=LEFT, padx=(0, 10))
        
        # Advanced search button
        advanced_search_btn = ttk.Button(basic_frame, text="⚙️ Advanced Search", style='warning.TButton')
        advanced_search_btn.pack(side=LEFT)
        
        # Second row - Advanced filters (initially hidden)
        advanced_frame = ttk.Frame(search_controls)
        
        # Date filters
        date_frame = ttk.LabelFrame(advanced_frame, text="Date Range", padding=10)
        date_frame.pack(fill=X, pady=(0, 10))
        
        date_row = ttk.Frame(date_frame)
        date_row.pack(fill=X)
        
        ttk.Label(date_row, text="From:").pack(side=LEFT, padx=(0, 5))
        date_from_entry = ttk.Entry(date_row, width=12)
        date_from_entry.pack(side=LEFT, padx=(0, 10))
        ttk.Label(date_row, text="To:").pack(side=LEFT, padx=(0, 5))
        date_to_entry = ttk.Entry(date_row, width=12)
        date_to_entry.pack(side=LEFT, padx=(0, 10))
        ttk.Label(date_row, text="(YYYY-MM-DD)", font=('Arial', 9), foreground='gray').pack(side=LEFT)
        
        # Type and access filters
        filter_frame = ttk.Frame(advanced_frame)
        filter_frame.pack(fill=X, pady=(0, 10))
        
        # Type filter
        type_frame = ttk.Frame(filter_frame)
        type_frame.pack(side=LEFT, padx=(0, 20))
        
        ttk.Label(type_frame, text="Item Type:").pack(side=LEFT, padx=(0, 5))
        item_type_var = tk.StringVar(value='all')
        item_type_combo = ttk.Combobox(type_frame, textvariable=item_type_var, 
                                      values=['all', 'app', 'folder', 'file'], 
                                      state='readonly', width=8)
        item_type_combo.pack(side=LEFT)
        
        # Access count filter
        access_frame = ttk.Frame(filter_frame)
        access_frame.pack(side=LEFT, padx=(0, 20))
        
        ttk.Label(access_frame, text="Access Count:").pack(side=LEFT, padx=(0, 5))
        min_access_entry = ttk.Entry(access_frame, width=5)
        min_access_entry.pack(side=LEFT, padx=(0, 5))
        ttk.Label(access_frame, text="to").pack(side=LEFT, padx=(0, 5))
        max_access_entry = ttk.Entry(access_frame, width=5)
        max_access_entry.pack(side=LEFT)
        
        # Sort options
        sort_frame = ttk.Frame(advanced_frame)
        sort_frame.pack(fill=X, pady=(0, 10))
        
        ttk.Label(sort_frame, text="Sort by:").pack(side=LEFT, padx=(0, 5))
        sort_by_var = tk.StringVar(value='name')
        sort_by_combo = ttk.Combobox(sort_frame, textvariable=sort_by_var, 
                                    values=['name', 'type', 'added_date', 'last_accessed', 'access_count'], 
                                    state='readonly', width=12)
        sort_by_combo.pack(side=LEFT, padx=(0, 10))
        
        ttk.Label(sort_frame, text="Order:").pack(side=LEFT, padx=(0, 5))
        sort_order_var = tk.StringVar(value='asc')
        sort_order_combo = ttk.Combobox(sort_frame, textvariable=sort_order_var, 
                                       values=['asc', 'desc'], 
                                       state='readonly', width=8)
        sort_order_combo.pack(side=LEFT)
        
        # Results frame
        results_frame = ttk.LabelFrame(frame, text="Search Results", padding=15)
        results_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Results header with count
        results_header = ttk.Frame(results_frame)
        results_header.pack(fill=X, pady=(0, 10))
        
        results_count_label = ttk.Label(results_header, text="Results: 0 items", font=('Arial', 11, 'bold'))
        results_count_label.pack(side=LEFT)
        
        # Export and save buttons
        export_btn = ttk.Button(results_header, text="📤 Export Results", style='info.TButton')
        export_btn.pack(side=RIGHT, padx=(0, 5))
        
        save_search_btn = ttk.Button(results_header, text="💾 Save Search", style='secondary.TButton')
        save_search_btn.pack(side=RIGHT)
        
        # Create scrollable results frame
        results_container = ttk.Frame(results_frame)
        results_container.pack(fill=BOTH, expand=True)
        
        # Tree frame with scrollbars
        tree_frame = ttk.Frame(results_container)
        tree_frame.pack(fill=BOTH, expand=True)
        
        # Enhanced results tree
        columns = ('Name', 'Type', 'Added', 'Last Accessed', 'Access Count', 'Path')
        results_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        results_tree.heading('Name', text='Name')
        results_tree.heading('Type', text='Type')
        results_tree.heading('Added', text='Added')
        results_tree.heading('Last Accessed', text='Last Accessed')
        results_tree.heading('Access Count', text='Access Count')
        results_tree.heading('Path', text='Original Path')
        
        results_tree.column('Name', width=200, minwidth=150)
        results_tree.column('Type', width=100, minwidth=80)
        results_tree.column('Added', width=150, minwidth=120)
        results_tree.column('Last Accessed', width=150, minwidth=120)
        results_tree.column('Access Count', width=100, minwidth=80)
        results_tree.column('Path', width=250, minwidth=200)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=results_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=results_tree.xview)
        results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        results_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Mouse wheel scrolling
        results_tree.bind('<MouseWheel>', lambda e: results_tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        results_tree.bind('<Shift-MouseWheel>', lambda e: results_tree.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        
        # Double-click to access item
        results_tree.bind('<Double-1>', lambda e: self.access_search_result(results_tree))
        
        # Saved searches frame
        saved_searches_frame = ttk.LabelFrame(frame, text="💾 Saved Searches", padding=15)
        saved_searches_frame.pack(fill=X, pady=(0, 20))
        
        saved_searches_listbox = tk.Listbox(saved_searches_frame, height=4, font=('Arial', 10))
        saved_searches_scrollbar = ttk.Scrollbar(saved_searches_frame, orient=VERTICAL, command=saved_searches_listbox.yview)
        saved_searches_listbox.configure(yscrollcommand=saved_searches_scrollbar.set)
        
        saved_searches_listbox.pack(side=LEFT, fill=BOTH, expand=True)
        saved_searches_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Load saved searches
        def load_saved_searches():
            saved_searches_listbox.delete(0, tk.END)
            saved_searches = self.vault_manager.get_saved_searches(self.current_user['username'])
            for search in saved_searches:
                saved_searches_listbox.insert(tk.END, f"{search['query']} ({search['use_count']} uses)")
        
        load_saved_searches()
        
        # Search functions
        def perform_advanced_search():
            query = search_entry.get().strip()
            search_type = search_type_var.get()
            date_from = date_from_entry.get().strip() or None
            date_to = date_to_entry.get().strip() or None
            item_type = item_type_var.get() if item_type_var.get() != 'all' else None
            min_access = int(min_access_entry.get()) if min_access_entry.get().strip() else None
            max_access = int(max_access_entry.get()) if max_access_entry.get().strip() else None
            sort_by = sort_by_var.get()
            sort_order = sort_order_var.get()
            
            # Get search parameters for saving
            search_params = {
                'search_type': search_type,
                'date_from': date_from,
                'date_to': date_to,
                'item_type': item_type,
                'min_access_count': min_access,
                'max_access_count': max_access,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
            
            if query:
                items = self.vault_manager.search_items(
                    query, self.current_user['username'], 
                    search_type=search_type,
                    date_from=date_from,
                    date_to=date_to,
                    item_type=item_type,
                    min_access_count=min_access,
                    max_access_count=max_access,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                
                # Clear results
                for item in results_tree.get_children():
                    results_tree.delete(item)
                
                # Add results
                for item in items:
                    type_icons = {'app': '📱', 'folder': '📁', 'file': '📄'}
                    type_display = f"{type_icons.get(item['item_type'], '❓')} {item['item_type'].title()}"
                    added_date = item['added_date'][:19] if item['added_date'] else 'N/A'
                    last_accessed = item['last_accessed'][:19] if item['last_accessed'] else 'Never'
                    
                    # Truncate path for display
                    path = item['original_path']
                    if len(path) > 50:
                        path = "..." + path[-47:]
                    
                    results_tree.insert('', 'end', values=(
                        item['name'], 
                        type_display, 
                        added_date, 
                        last_accessed, 
                        item['access_count'],
                        path
                    ), tags=(item['id'],))
                
                # Update count
                results_count_label.config(text=f"Results: {len(items)} items")
                
                # Save search if it has results
                if items:
                    self.vault_manager.save_search_query(self.current_user['username'], query, search_params)
                    load_saved_searches()
        
        def perform_quick_search():
            query = search_entry.get().strip()
            if query:
                items = self.vault_manager.search_items_simple(query, self.current_user['username'])
                
                # Clear results
                for item in results_tree.get_children():
                    results_tree.delete(item)
                
                # Add results
                for item in items:
                    type_icons = {'app': '📱', 'folder': '📁', 'file': '📄'}
                    type_display = f"{type_icons.get(item['item_type'], '❓')} {item['item_type'].title()}"
                    added_date = item['added_date'][:19] if item['added_date'] else 'N/A'
                    last_accessed = item['last_accessed'][:19] if item['last_accessed'] else 'Never'
                    
                    # Truncate path for display
                    path = item['original_path']
                    if len(path) > 50:
                        path = "..." + path[-47:]
                    
                    results_tree.insert('', 'end', values=(
                        item['name'], 
                        type_display, 
                        added_date, 
                        last_accessed, 
                        item['access_count'],
                        path
                    ), tags=(item['id'],))
                
                # Update count
                results_count_label.config(text=f"Results: {len(items)} items")
        
        def toggle_advanced_filters():
            if advanced_frame.winfo_ismapped():
                advanced_frame.pack_forget()
                advanced_search_btn.config(text="⚙️ Show Advanced")
            else:
                advanced_frame.pack(fill=X, pady=(10, 0))
                advanced_search_btn.config(text="⚙️ Hide Advanced")
        
        def show_statistics():
            stats = self.vault_manager.get_search_statistics(self.current_user['username'])
            
            stats_window = tk.Toplevel(search_window)
            stats_window.title("📊 Vault Statistics")
            stats_window.geometry("500x400")
            stats_window.transient(search_window)
            stats_window.grab_set()
            
            # Center window
            stats_window.update_idletasks()
            x = (stats_window.winfo_screenwidth() // 2) - 250
            y = (stats_window.winfo_screenheight() // 2) - 200
            stats_window.geometry(f'500x400+{x}+{y}')
            
            stats_frame = ttk.Frame(stats_window, padding=20)
            stats_frame.pack(fill=BOTH, expand=True)
            
            ttk.Label(stats_frame, text="📊 Vault Statistics", font=('Arial', 16, 'bold')).pack(pady=(0, 20))
            
            # Statistics content
            stats_text = f"""
📈 Overview:
  • Total Items: {stats.get('total_items', 0)}
  • Recent Items (30 days): {stats.get('recent_items', 0)}

📁 Items by Type:
  • Applications: {stats.get('items_by_type', {}).get('app', 0)}
  • Folders: {stats.get('items_by_type', {}).get('folder', 0)}
  • Files: {stats.get('items_by_type', {}).get('file', 0)}

📅 Items by Date:
  • Last 7 days: {stats.get('items_by_date', {}).get('Last 7 days', 0)}
  • Last 30 days: {stats.get('items_by_date', {}).get('Last 30 days', 0)}
  • Last 90 days: {stats.get('items_by_date', {}).get('Last 90 days', 0)}
  • Older: {stats.get('items_by_date', {}).get('Older', 0)}

🔥 Most Accessed Items:
"""
            
            for name, count in stats.get('most_accessed', []):
                stats_text += f"  • {name}: {count} accesses\n"
            
            # Create scrollable text widget
            text_container = ttk.Frame(stats_frame)
            text_container.pack(fill=BOTH, expand=True)
            
            text_widget = tk.Text(text_container, wrap=tk.WORD, font=('Consolas', 10))
            scrollbar = ttk.Scrollbar(text_container, orient=VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=LEFT, fill=BOTH, expand=True)
            scrollbar.pack(side=RIGHT, fill=Y)
            
            text_widget.insert(tk.END, stats_text)
            text_widget.config(state=tk.DISABLED)
            
            # Control buttons frame
            control_frame = ttk.Frame(stats_frame)
            control_frame.pack(fill=X, pady=(10, 0))
            
            # Left side - Window control buttons
            window_controls = ttk.Frame(control_frame)
            window_controls.pack(side=tk.LEFT)
            
            # Minimize button
            def minimize_window():
                stats_window.iconify()
            ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Maximize/Restore button
            is_maximized = False
            def toggle_maximize():
                nonlocal is_maximized
                if is_maximized:
                    stats_window.geometry("500x400")
                    is_maximized = False
                else:
                    stats_window.state('zoomed')
                    is_maximized = True
            ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
            
            # Right side - Close button
            ttk.Button(control_frame, text="Close", command=stats_window.destroy, 
                      style='primary.TButton').pack(side=tk.RIGHT)
            
            # Handle window close event
            def on_stats_close():
                stats_window.destroy()
            
            stats_window.protocol("WM_DELETE_WINDOW", on_stats_close)
        
        def access_search_result(tree):
            """Access selected search result"""
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an item to access")
                return
            
            item_id = tree.item(selection[0])['tags'][0]
            
            # Verify 2FA before access
            self.verify_otp_for_sensitive_action(lambda: self.access_item(item_id))
        
        # Bind buttons
        quick_search_btn.config(command=perform_quick_search)
        advanced_search_btn.config(command=toggle_advanced_filters)
        stats_btn.config(command=show_statistics)
        
        # Bind Enter key to quick search
        search_entry.focus()
        search_window.bind('<Return>', lambda e: perform_quick_search())
        
        # Unbind mousewheel when window closes
        def on_closing():
            canvas.unbind_all("<MouseWheel>")
            search_window.destroy()
        
        search_window.protocol("WM_DELETE_WINDOW", on_closing)
    
    def show_logs_dialog(self):
        """Show enhanced logs dialog with tabs, filtering, analytics, and export"""
        import csv
        from tkinter import simpledialog
        logs_window = tk.Toplevel(self.root)
        logs_window.title("Vault Logs & Analytics")
        logs_window.geometry("1100x800")
        logs_window.transient(self.root)
        logs_window.resizable(True, True)
        logs_window.grab_set()

        # Center window
        logs_window.update_idletasks()
        x = (logs_window.winfo_screenwidth() // 2) - 550
        y = (logs_window.winfo_screenheight() // 2) - 400
        logs_window.geometry(f'1100x800+{x}+{y}')

        # Tabs for log types
        notebook = ttk.Notebook(logs_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Helper for log color ---
        def get_log_color(level):
            if level in ("ERROR", "SECURITY"): return "#ffcccc"
            if level == "WARNING": return "#fff2cc"
            if level == "INFO": return "#e6f7ff"
            return "#f4f4f4"

        # --- Access Logs Tab ---
        access_frame = ttk.Frame(notebook)
        notebook.add(access_frame, text="Access Logs")
        # --- Security Logs Tab ---
        security_frame = ttk.Frame(notebook)
        notebook.add(security_frame, text="Security Logs")
        # --- System Logs Tab ---
        system_frame = ttk.Frame(notebook)
        notebook.add(system_frame, text="System Logs")

        # --- Analytics/Stats Panel ---
        stats_frame = ttk.LabelFrame(logs_window, text="Log Analytics & Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        stats_label = ttk.Label(stats_frame, text="", font=("Consolas", 11))
        stats_label.pack(anchor=tk.W)

        # --- Controls (shared) ---
        control_frame = ttk.Frame(logs_window)
        control_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0,10))
        ttk.Label(control_frame, text="Date from:").pack(side=tk.LEFT)
        date_from_var = tk.StringVar()
        date_from_entry = ttk.Entry(control_frame, textvariable=date_from_var, width=12)
        date_from_entry.pack(side=tk.LEFT, padx=(0,5))
        ttk.Label(control_frame, text="to").pack(side=tk.LEFT)
        date_to_var = tk.StringVar()
        date_to_entry = ttk.Entry(control_frame, textvariable=date_to_var, width=12)
        date_to_entry.pack(side=tk.LEFT, padx=(0,10))
        ttk.Label(control_frame, text="User:").pack(side=tk.LEFT)
        user_var = tk.StringVar(value="All")
        user_entry = ttk.Entry(control_frame, textvariable=user_var, width=12)
        user_entry.pack(side=tk.LEFT, padx=(0,10))
        auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_btn = ttk.Checkbutton(control_frame, text="Auto-Refresh", variable=auto_refresh_var)
        auto_refresh_btn.pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(control_frame, text="Export CSV", command=lambda: self.export_logs_to_csv(all_logs)).pack(side=tk.RIGHT, padx=(0,5))
        ttk.Button(control_frame, text="Export JSON", command=lambda: self.export_logs_to_json(all_logs)).pack(side=tk.RIGHT, padx=(0,5))

        # --- Treeview setup helper ---
        def setup_tree(parent, columns, headings):
            tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
            for col, head in zip(columns, headings):
                tree.heading(col, text=head)
                tree.column(col, width=160, minwidth=80)
            v_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
            h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
            tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
            tree.grid(row=0, column=0, sticky='nsew')
            v_scroll.grid(row=0, column=1, sticky='ns')
            h_scroll.grid(row=1, column=0, sticky='ew')
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
            return tree

        # --- Load all logs (access, security, system/info) ---
        all_logs = []
        def load_all_logs():
            nonlocal all_logs
            # Access logs from vault_manager
            access_logs = self.vault_manager.get_access_logs(self.current_user['username'], limit=500)
            for log in access_logs:
                log['level'] = 'INFO' if log.get('success', True) else 'WARNING'
                log['type'] = 'Access'
                log['user'] = self.current_user['username']
            # Security logs from logger
            security_logs = self.logger.get_recent_logs(hours=168, level='SECURITY')
            for log in security_logs:
                log['level'] = 'SECURITY'
                log['type'] = 'Security'
                log['user'] = log.get('user', self.current_user['username'])
            # System logs (INFO, WARNING, ERROR)
            system_logs = self.logger.get_recent_logs(hours=168)
            for log in system_logs:
                if log['level'] not in ('SECURITY',):
                    log['type'] = 'System'
                    log['user'] = log.get('user', self.current_user['username'])
            all_logs = access_logs + security_logs + [l for l in system_logs if l['level'] != 'SECURITY']

        # --- Filtering and search ---
        def filter_logs(logs, log_type):
            q = search_var.get().lower()
            df = date_from_var.get().strip()
            dt = date_to_var.get().strip()
            user = user_var.get().strip()
            filtered = []
            for log in logs:
                if log_type and log.get('type') != log_type:
                    continue
                if q and q not in str(log).lower():
                    continue
                if user and user != 'All' and user.lower() not in str(log.get('user', '')).lower():
                    continue
                # Date filter
                log_time = log.get('timestamp') or log.get('access_time')
                if log_time:
                    try:
                        log_dt = datetime.fromisoformat(log_time[:19])
                        if df:
                            df_dt = datetime.fromisoformat(df)
                            if log_dt < df_dt:
                                continue
                        if dt:
                            dt_dt = datetime.fromisoformat(dt)
                            if log_dt > dt_dt:
                                continue
                    except Exception:
                        pass
                filtered.append(log)
            return filtered

        # --- Treeviews for each tab ---
        access_tree = setup_tree(access_frame, ['Item', 'Time', 'Type', 'Status', 'User'], ['Item', 'Time', 'Type', 'Status', 'User'])
        security_tree = setup_tree(security_frame, ['Time', 'Level', 'Event', 'Message', 'User'], ['Time', 'Level', 'Event', 'Message', 'User'])
        system_tree = setup_tree(system_frame, ['Time', 'Level', 'Message', 'User'], ['Time', 'Level', 'Message', 'User'])

        # --- Populate trees ---
        def refresh_all():
            load_all_logs()
            # Access
            access_tree.delete(*access_tree.get_children())
            for log in filter_logs(all_logs, 'Access'):
                status = "✅ Success" if log.get('success', True) else "❌ Failed"
                access_tree.insert('', 'end', values=(log.get('item_name',''), log.get('access_time',''), log.get('access_type',''), status, log.get('user','')), tags=(log.get('level','INFO'),))
            # Security
            security_tree.delete(*security_tree.get_children())
            for log in filter_logs(all_logs, 'Security'):
                security_tree.insert('', 'end', values=(log.get('timestamp',''), log.get('level',''), log.get('event_type',''), log.get('message',''), log.get('user','')), tags=(log.get('level','SECURITY'),))
            # System
            system_tree.delete(*system_tree.get_children())
            for log in filter_logs(all_logs, 'System'):
                system_tree.insert('', 'end', values=(log.get('timestamp',''), log.get('level',''), log.get('message',''), log.get('user','')), tags=(log.get('level','INFO'),))
            # Stats
            stats = self.logger.get_security_summary()
            stats_text = f"Total Security Events: {stats.get('total_security_events',0)}\nFailed Logins: {stats.get('failed_logins',0)}\nTamper Attempts: {stats.get('tamper_attempts',0)}\nSuspicious Access: {stats.get('suspicious_access',0)}\n\nRecent Security Events:\n" + '\n'.join([f"{e.get('timestamp','')}: {e.get('event_type','')} - {e.get('message','')}" for e in stats.get('last_24h_events',[])])
            stats_label.config(text=stats_text)

        # --- Color rows by log level ---
        def colorize_tree(tree):
            for iid in tree.get_children():
                level = tree.item(iid, 'tags')[0] if tree.item(iid, 'tags') else 'INFO'
                tree.tag_configure(level, background=get_log_color(level))

        # --- Double-click for details ---
        def show_log_details(event, tree):
            item = tree.focus()
            if not item:
                return
            values = tree.item(item, 'values')
            detail = '\n'.join(f"{col}: {val}" for col, val in zip(tree['columns'], values))
            messagebox.showinfo("Log Details", detail)

        for tree in [access_tree, security_tree, system_tree]:
            tree.bind('<Double-1>', lambda e, t=tree: show_log_details(e, t))

        # --- Export helpers ---
        def export_logs_to_csv(logs):
            file = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV Files', '*.csv')])
            if not file:
                return
            if not logs:
                messagebox.showwarning("No logs", "No logs to export.")
                return
            keys = set()
            for log in logs:
                keys.update(log.keys())
            keys = list(keys)
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(logs)
            messagebox.showinfo("Exported", f"Logs exported to {file}")
        def export_logs_to_json(logs):
            file = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON Files', '*.json')])
            if not file:
                return
            if not logs:
                messagebox.showwarning("No logs", "No logs to export.")
                return
            import json
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2)
            messagebox.showinfo("Exported", f"Logs exported to {file}")
        self.export_logs_to_csv = export_logs_to_csv
        self.export_logs_to_json = export_logs_to_json

        # --- Refresh logic ---
        def periodic_refresh():
            if auto_refresh_var.get():
                refresh_all()
                colorize_tree(access_tree)
                colorize_tree(security_tree)
                colorize_tree(system_tree)
            logs_window.after(5000, periodic_refresh)
        periodic_refresh()

        # --- Manual refresh and search triggers ---
        search_var.trace('w', lambda *a: refresh_all())
        date_from_var.trace('w', lambda *a: refresh_all())
        date_to_var.trace('w', lambda *a: refresh_all())
        user_var.trace('w', lambda *a: refresh_all())
        auto_refresh_var.trace('w', lambda *a: refresh_all())

        # Initial load
        refresh_all()
    
    def show_settings_dialog(self):
        """Show settings dialog with enhanced sidebar navigation, icons, dividers, tooltips, and status indicators"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("800x600")
        settings_window.transient(self.root)
        settings_window.resizable(True, True)

        # Center window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - 400
        y = (settings_window.winfo_screenheight() // 2) - 300
        settings_window.geometry(f'800x600+{x}+{y}')

        # Main container
        main_container = ttk.Frame(settings_window)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar for navigation
        sidebar = ttk.Frame(main_container, width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0), pady=20)
        sidebar.pack_propagate(False)

        # Content area (with scroll)
        content_container = ttk.Frame(main_container)
        content_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create canvas for scrolling
        canvas = tk.Canvas(content_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Unbind mousewheel on close to prevent TclError
        def on_settings_close():
            canvas.unbind_all("<MouseWheel>")
            settings_window.destroy()
        settings_window.protocol("WM_DELETE_WINDOW", on_settings_close)

        # Tabs and icons
        tab_defs = [
            ("Security", "🔒"),
            ("Profile", "👤"),
            ("Account Security", "🔐"),
            ("General", "⚙️"),
            ("Advanced", "🔧")
        ]
        tab_frames = {}
        selected_tab = tk.StringVar(value=tab_defs[0][0])

        # --- Create all tab frames first ---
        # --- Security Tab ---
        security_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Security"] = security_frame
        # --- Profile Tab ---
        profile_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Profile"] = profile_frame
        # --- Account Security Tab ---
        account_security_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Account Security"] = account_security_frame
        # --- General Tab ---
        general_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["General"] = general_frame
        # --- Advanced Tab ---
        advanced_frame = ttk.Frame(scrollable_frame, padding=10)
        tab_frames["Advanced"] = advanced_frame

        def show_tab(tab_name):
            for name, frame in tab_frames.items():
                frame.pack_forget()
            tab_frames[tab_name].pack(fill=tk.BOTH, expand=True)
            selected_tab.set(tab_name)

        # Sidebar navigation buttons
        for tab_name, icon in tab_defs:
            btn = ttk.Button(
                sidebar,
                text=f"{icon}  {tab_name}",
                style='TButton',
                command=lambda n=tab_name: show_tab(n)
            )
            btn.pack(fill=tk.X, pady=6, anchor=tk.N)
            # TODO: Add tooltip: f"Go to {tab_name} settings" (custom tooltip class)

        # --- Security Tab ---
        # Section header with icon
        ttk.Label(security_frame, text="🔒 Security Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(security_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        # Auto-lock timeout
        timeout_frame = ttk.LabelFrame(security_frame, text="Auto-Lock Settings", padding=15)
        timeout_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(timeout_frame, text="Auto-lock timeout (minutes):").pack(anchor=tk.W, pady=(0, 5))
        timeout_var = tk.StringVar(value=str(self.config.get('auto_lock_timeout', 300) // 60))
        timeout_entry = ttk.Entry(timeout_frame, textvariable=timeout_var, width=10)
        timeout_entry.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(timeout_frame, text="Set to 0 to disable auto-lock", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        # 2FA settings
        twofa_frame = ttk.LabelFrame(security_frame, text="Two-Factor Authentication", padding=15)
        twofa_frame.pack(fill=tk.X, pady=(0, 15))
        require_2fa_var = tk.BooleanVar(value=self.config.get('require_2fa', True))
        twofa_check = ttk.Checkbutton(twofa_frame, text="Require 2FA for all actions", variable=require_2fa_var)
        twofa_check.pack(anchor=tk.W, pady=2)
        has_2fa = self.auth_manager.current_user and self.auth_manager.current_user.get('totp_secret')
        if has_2fa:
            ttk.Label(twofa_frame, text="✅ 2FA is enabled for your account", font=('Arial', 10), foreground='green').pack(anchor=tk.W, pady=5)
        else:
            ttk.Label(twofa_frame, text="❌ 2FA is not enabled for your account", font=('Arial', 10), foreground='red').pack(anchor=tk.W, pady=5)
            setup_2fa_btn = ttk.Button(twofa_frame, text="🔐 Set Up 2FA Now", command=lambda: [settings_window.destroy(), self.show_2fa_setup_dialog()], style='success.TButton')
            setup_2fa_btn.pack(anchor=tk.W, pady=5)
        # Change master password
        password_frame = ttk.LabelFrame(security_frame, text="Change Master Password", padding=15)
        password_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(password_frame, text="Change your master password:").pack(anchor=tk.W, pady=(0, 5))
        old_pass_var = tk.StringVar()
        new_pass_var = tk.StringVar()
        confirm_pass_var = tk.StringVar()
        ttk.Label(password_frame, text="Current Password:").pack(anchor=tk.W)
        old_pass_entry = ttk.Entry(password_frame, textvariable=old_pass_var, show='*')
        old_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(password_frame, text="New Password:").pack(anchor=tk.W)
        new_pass_entry = ttk.Entry(password_frame, textvariable=new_pass_var, show='*')
        new_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(password_frame, text="Confirm New Password:").pack(anchor=tk.W)
        confirm_pass_entry = ttk.Entry(password_frame, textvariable=confirm_pass_var, show='*')
        confirm_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        def change_password():
            old = old_pass_var.get()
            new = new_pass_var.get()
            confirm = confirm_pass_var.get()
            if not old or not new or not confirm:
                messagebox.showerror("Error", "All password fields are required.")
                return
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.")
                return
            # Call backend to change password
            if self.auth_manager.current_user:
                username = self.auth_manager.current_user.get('username')
                success, msg = self.auth_manager.perform_password_change(old, new)
                if success:
                    messagebox.showinfo("Success", "Password changed successfully.")
                    old_pass_var.set("")
                    new_pass_var.set("")
                    confirm_pass_var.set("")
                else:
                    messagebox.showerror("Error", msg)
            else:
                messagebox.showerror("Error", "No user logged in.")
        ttk.Button(password_frame, text="Change Password", command=change_password, style='success.TButton').pack(anchor=tk.W, pady=(5, 0))
        # Biometric unlock (placeholder)
        bio_frame = ttk.LabelFrame(security_frame, text="Biometric Unlock", padding=15)
        bio_frame.pack(fill=tk.X, pady=(0, 15))
        bio_var = tk.BooleanVar(value=self.config.get('enable_biometric', False))
        bio_check = ttk.Checkbutton(bio_frame, text="Enable biometric unlock (fingerprint/face)", variable=bio_var, state='disabled')
        bio_check.pack(anchor=tk.W, pady=2)
        ttk.Label(bio_frame, text="(Biometric unlock support coming soon)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        # Email alerts
        alerts_frame = ttk.LabelFrame(security_frame, text="Email Alerts", padding=15)
        alerts_frame.pack(fill=tk.X, pady=(0, 15))
        alerts_var = tk.BooleanVar(value=self.config.get('enable_email_alerts', False))
        alerts_check = ttk.Checkbutton(alerts_frame, text="Enable email alerts for suspicious activity", variable=alerts_var)
        alerts_check.pack(anchor=tk.W, pady=2)

        # --- Profile Tab ---
        # Section header with icon
        ttk.Label(profile_frame, text="👤 User Profile", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(profile_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        # Profile fields frame
        personal_frame = ttk.LabelFrame(profile_frame, text="Personal Information", padding=15)
        personal_frame.pack(fill=tk.X, pady=(0, 20))
        # Load current user profile values
        user_profile = None
        if self.auth_manager.current_user:
            username = self.auth_manager.current_user.get('username')
            user_profile = self.auth_manager.get_user_profile(username)
        else:
            username = None
        # Email
        ttk.Label(personal_frame, text="Email Address:").pack(anchor=tk.W, pady=(0, 5))
        email_var = tk.StringVar(value=(user_profile['email'] if user_profile and user_profile.get('email') else ''))
        email_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=email_var)
        email_entry.pack(fill=tk.X, pady=(0, 5))
        email_feedback = ttk.Label(personal_frame, text="", font=('Arial', 9))
        email_feedback.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(personal_frame, text="Used for password recovery and 2FA", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        # Mobile Number
        ttk.Label(personal_frame, text="Mobile Number:").pack(anchor=tk.W, pady=(0, 5))
        mobile_var = tk.StringVar(value=(user_profile['mobile_number'] if user_profile and user_profile.get('mobile_number') else ''))
        mobile_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=mobile_var)
        mobile_entry.pack(fill=tk.X, pady=(0, 5))
        mobile_feedback = ttk.Label(personal_frame, text="", font=('Arial', 9))
        mobile_feedback.pack(anchor=tk.W, pady=(0, 10))
        ttk.Label(personal_frame, text="Format: +1 (555) 123-4567 or 5551234567", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        # Full Name
        ttk.Label(personal_frame, text="Full Name:").pack(anchor=tk.W, pady=(15, 5))
        fullname_var = tk.StringVar(value=(user_profile['user_data'].get('fullname') if user_profile and user_profile.get('user_data') and user_profile['user_data'].get('fullname') else ''))
        fullname_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=fullname_var)
        fullname_entry.pack(fill=tk.X, pady=(0, 15))
        # Organization
        ttk.Label(personal_frame, text="Organization:").pack(anchor=tk.W, pady=(0, 5))
        org_var = tk.StringVar(value=(user_profile['user_data'].get('organization') if user_profile and user_profile.get('user_data') and user_profile['user_data'].get('organization') else ''))
        org_entry = ttk.Entry(personal_frame, font=('Arial', 12), textvariable=org_var)
        org_entry.pack(fill=tk.X, pady=(0, 15))
        # Inline validation functions
        def validate_email(*args):
            email = email_var.get().strip()
            if not email:
                email_feedback.config(text="", foreground="black")
                email_entry.config(foreground="black")
                return
            pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if re.match(pattern, email):
                email_feedback.config(text="✔ Valid email", foreground="green")
                email_entry.config(foreground="green")
            else:
                email_feedback.config(text="✖ Invalid email format", foreground="red")
                email_entry.config(foreground="red")
        email_var.trace_add('write', validate_email)
        def validate_mobile(*args):
            mobile = mobile_var.get().strip()
            if not mobile:
                mobile_feedback.config(text="", foreground="black")
                mobile_entry.config(foreground="black")
                return
            pattern = r"^(\+\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}$"
            if re.match(pattern, mobile):
                mobile_feedback.config(text="✔ Valid phone number", foreground="green")
                mobile_entry.config(foreground="green")
            else:
                mobile_feedback.config(text="✖ Invalid phone number", foreground="red")
                mobile_entry.config(foreground="red")
        mobile_var.trace_add('write', validate_mobile)
        # Save Profile button
        def save_profile():
            if not username:
                messagebox.showerror("Error", "No user logged in.")
                return
            user_data = user_profile['user_data'] if user_profile and user_profile.get('user_data') else {}
            user_data['fullname'] = fullname_var.get()
            user_data['organization'] = org_var.get()
            success, msg = self.auth_manager.update_user_profile(
                username,
                email=email_var.get(),
                mobile_number=mobile_var.get(),
                user_data=user_data
            )
            if success:
                messagebox.showinfo("Profile Updated", "Your profile has been updated successfully.")
            else:
                messagebox.showerror("Error", msg)
        ttk.Button(personal_frame, text="Save Profile", command=save_profile, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))

        # --- Account Security Tab ---
        # Section header with icon
        ttk.Label(account_security_frame, text="🔐 Account Security Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(account_security_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        # Change password
        pw_frame = ttk.LabelFrame(account_security_frame, text="Change Password", padding=15)
        pw_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(pw_frame, text="Change your account password:").pack(anchor=tk.W, pady=(0, 5))
        acc_old_pass_var = tk.StringVar()
        acc_new_pass_var = tk.StringVar()
        acc_confirm_pass_var = tk.StringVar()
        ttk.Label(pw_frame, text="Current Password:").pack(anchor=tk.W)
        acc_old_pass_entry = ttk.Entry(pw_frame, textvariable=acc_old_pass_var, show='*')
        acc_old_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(pw_frame, text="New Password:").pack(anchor=tk.W)
        acc_new_pass_entry = ttk.Entry(pw_frame, textvariable=acc_new_pass_var, show='*')
        acc_new_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(pw_frame, text="Confirm New Password:").pack(anchor=tk.W)
        acc_confirm_pass_entry = ttk.Entry(pw_frame, textvariable=acc_confirm_pass_var, show='*')
        acc_confirm_pass_entry.pack(anchor=tk.W, pady=(0, 5))
        def acc_change_password():
            old = acc_old_pass_var.get()
            new = acc_new_pass_var.get()
            confirm = acc_confirm_pass_var.get()
            if not old or not new or not confirm:
                messagebox.showerror("Error", "All password fields are required.")
                return
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.")
                return
            if self.auth_manager.current_user:
                username = self.auth_manager.current_user.get('username')
                success, msg = self.auth_manager.perform_password_change(old, new)
                if success:
                    messagebox.showinfo("Success", "Password changed successfully.")
                    acc_old_pass_var.set("")
                    acc_new_pass_var.set("")
                    acc_confirm_pass_var.set("")
                else:
                    messagebox.showerror("Error", msg)
            else:
                messagebox.showerror("Error", "No user logged in.")
        ttk.Button(pw_frame, text="Change Password", command=acc_change_password, style='success.TButton').pack(anchor=tk.W, pady=(5, 0))
        # 2FA controls
        twofa_frame = ttk.LabelFrame(account_security_frame, text="Two-Factor Authentication (2FA)", padding=15)
        twofa_frame.pack(fill=tk.X, pady=(0, 15))
        has_2fa = self.auth_manager.current_user and self.auth_manager.current_user.get('totp_secret')
        if has_2fa:
            ttk.Label(twofa_frame, text="✅ 2FA is enabled for your account", font=('Arial', 10), foreground='green').pack(anchor=tk.W, pady=5)
            ttk.Button(twofa_frame, text="Disable 2FA", command=lambda: messagebox.showinfo("Coming Soon", "Disabling 2FA will be available in a future update."), style='danger.TButton').pack(anchor=tk.W, pady=2)
            ttk.Button(twofa_frame, text="Reset 2FA (Lost Device)", command=lambda: messagebox.showinfo("Coming Soon", "2FA reset will be available in a future update."), style='warning.TButton').pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(twofa_frame, text="❌ 2FA is not enabled for your account", font=('Arial', 10), foreground='red').pack(anchor=tk.W, pady=5)
            ttk.Button(twofa_frame, text="Enable 2FA", command=lambda: [settings_window.destroy(), self.show_2fa_setup_dialog()], style='success.TButton').pack(anchor=tk.W, pady=2)
        # Recent login activity (placeholder)
        login_frame = ttk.LabelFrame(account_security_frame, text="Recent Login Activity", padding=15)
        login_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(login_frame, text="(Recent login activity will appear here in a future update.)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)

        # --- General Tab ---
        ttk.Label(general_frame, text="⚙️ General Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(general_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        # Theme selection
        theme_frame = ttk.LabelFrame(general_frame, text="Theme", padding=15)
        theme_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(theme_frame, text="Select application theme:").pack(anchor=tk.W)
        theme_var = tk.StringVar(value=self.config.get('theme', 'darkly'))
        theme_options = ['darkly', 'flatly', 'cosmo', 'cyborg', 'journal', 'litera', 'lumen', 'minty', 'pulse', 'sandstone', 'simplex', 'slate', 'solar', 'spacelab', 'superhero', 'united', 'yeti']
        theme_menu = ttk.Combobox(theme_frame, textvariable=theme_var, values=theme_options, state='readonly')
        theme_menu.pack(anchor=tk.W, pady=(5, 0))
        # Language selection (placeholder)
        lang_frame = ttk.LabelFrame(general_frame, text="Language", padding=15)
        lang_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(lang_frame, text="Select application language:").pack(anchor=tk.W)
        lang_var = tk.StringVar(value='English')
        lang_menu = ttk.Combobox(lang_frame, textvariable=lang_var, values=['English'], state='readonly')
        lang_menu.pack(anchor=tk.W, pady=(5, 0))
        ttk.Label(lang_frame, text="(More languages coming soon)", font=('Arial', 9), foreground='gray').pack(anchor=tk.W)
        # Window size
        win_frame = ttk.LabelFrame(general_frame, text="Window Size", padding=15)
        win_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(win_frame, text="Set main window size (e.g., 1200x800):").pack(anchor=tk.W)
        window_size_var = tk.StringVar(value=self.config.get('window_size', '1200x800'))
        window_size_entry = ttk.Entry(win_frame, textvariable=window_size_var)
        window_size_entry.pack(anchor=tk.W, pady=(5, 0))
        # Notifications toggle (placeholder)
        notif_frame = ttk.LabelFrame(general_frame, text="Notifications", padding=15)
        notif_frame.pack(fill=tk.X, pady=(0, 15))
        notif_var = tk.BooleanVar(value=False)
        notif_check = ttk.Checkbutton(notif_frame, text="Enable desktop notifications (coming soon)", variable=notif_var, state='disabled')
        notif_check.pack(anchor=tk.W, pady=2)
        # Save General Settings button
        def save_general():
            self.config.set('theme', theme_var.get())
            self.config.set('window_size', window_size_var.get())
            messagebox.showinfo("General Settings Saved", "Theme and window size have been saved. Please restart the app to apply theme changes.")
        ttk.Button(general_frame, text="Save General Settings", command=save_general, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))
        # --- Advanced Tab ---
        ttk.Label(advanced_frame, text="🔧 Advanced Settings", font=('Arial', 15, 'bold')).pack(anchor=tk.W, pady=(0, 16))
        ttk.Separator(advanced_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))
        # Export/Import vault (placeholders)
        vault_frame = ttk.LabelFrame(advanced_frame, text="Vault Data", padding=15)
        vault_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Button(vault_frame, text="Export Vault Data", command=lambda: messagebox.showinfo("Coming Soon", "Vault export will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(vault_frame, text="Import Vault Data", command=lambda: messagebox.showinfo("Coming Soon", "Vault import will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        # Backup/Restore (placeholders)
        backup_frame = ttk.LabelFrame(advanced_frame, text="Backup & Restore", padding=15)
        backup_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Button(backup_frame, text="Backup Now", command=lambda: messagebox.showinfo("Coming Soon", "Backup will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        ttk.Button(backup_frame, text="Restore Backup", command=lambda: messagebox.showinfo("Coming Soon", "Restore will be available in a future update."), style='info.TButton').pack(anchor=tk.W, pady=(0, 5))
        # Log level selection
        log_frame = ttk.LabelFrame(advanced_frame, text="Logging", padding=15)
        log_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(log_frame, text="Log level:").pack(anchor=tk.W)
        log_level_var = tk.StringVar(value=self.config.get('log_level', 'INFO'))
        log_level_menu = ttk.Combobox(log_frame, textvariable=log_level_var, values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], state='readonly')
        log_level_menu.pack(anchor=tk.W, pady=(5, 0))
        # Debug mode toggle
        debug_var = tk.BooleanVar(value=self.config.get('debug_mode', False))
        debug_check = ttk.Checkbutton(log_frame, text="Enable debug mode", variable=debug_var)
        debug_check.pack(anchor=tk.W, pady=2)
        # Save Advanced Settings button
        def save_advanced():
            self.config.set('log_level', log_level_var.get())
            self.config.set('debug_mode', debug_var.get())
            messagebox.showinfo("Advanced Settings Saved", "Log level and debug mode have been saved.")
        ttk.Button(advanced_frame, text="Save Advanced Settings", command=save_advanced, style='success.TButton').pack(anchor=tk.E, pady=(10, 0))
        
        # Define reset_to_defaults function first

        
        # Reset all settings button
        ttk.Button(advanced_frame, text="Reset All Settings to Default", command=reset_to_defaults, style='danger.TButton').pack(anchor=tk.E, pady=(10, 0))

        # Show the first tab by default
        show_tab(tab_defs[0][0])

        # --- Button frame ---
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        # Define default values (should match Config defaults)
        defaults = {
            'auto_lock_timeout': 300,
            'require_2fa': True,
            'theme': 'darkly',
            'window_size': '1200x800',
            'enable_sms_otp': False,
            'twilio_account_sid': '',
            'twilio_auth_token': '',
            'twilio_phone_number': '',
            'log_level': 'INFO',
            # Profile defaults (for next steps)
            'email': '',
            'mobile_number': '',
            'fullname': '',
            'organization': ''
        }
        timeout_var.set(str(defaults['auto_lock_timeout'] // 60))
        require_2fa_var.set(defaults['require_2fa'])
        theme_var.set(defaults['theme'])
        window_size_var.set(defaults['window_size'])
        enable_sms_var.set(defaults['enable_sms_otp'])
        twilio_sid_var.set(defaults['twilio_account_sid'])
        twilio_token_var.set(defaults['twilio_auth_token'])
        twilio_phone_var.set(defaults['twilio_phone_number'])
        log_level_var.set(defaults['log_level'])
        debug_var.set(defaults['debug_mode'])
        email_var.set(defaults['email'])
        mobile_var.set(defaults['mobile_number'])
        fullname_var.set(defaults['fullname'])
        org_var.set(defaults['organization'])
        
        def reset_to_defaults():
            """Reset all settings to their default values"""
            # Reset config fields
            for key, value in defaults.items():
                self.config.set(key, value)
            # Reset user profile fields
            if username:
                user_data = user_profile['user_data'] if user_profile and user_profile.get('user_data') else {}
                user_data['fullname'] = defaults['fullname']
                user_data['organization'] = defaults['organization']
                self.auth_manager.update_user_profile(
                    username,
                    email=defaults['email'],
                    mobile_number=defaults['mobile_number'],
                    user_data=user_data
                )
            messagebox.showinfo("Reset to Defaults", "All settings have been reset to their default values. Click 'Save Settings' to apply.")

        def save_settings():
            """Save all settings to the config file"""
            # Save config fields
            try:
                timeout_val = int(timeout_var.get())
                self.config.set('auto_lock_timeout', timeout_val * 60)
                twilio_phone_var.set(defaults['twilio_phone_number'])
                log_level_var.set(defaults['log_level'])
            except Exception:
                pass
            # Profile fields (if present)
            try:
                email_var.set(defaults['email'])
                mobile_var.set(defaults['mobile_number'])
                fullname_var.set(defaults['fullname'])
                org_var.set(defaults['organization'])
            except Exception:
                pass
            messagebox.showinfo("Reset to Defaults", "All settings have been reset to their default values. Click 'Save Settings' to apply.")

        def save_settings():
            # Save config fields
            try:
                timeout_val = int(timeout_var.get())
                self.config.set('auto_lock_timeout', timeout_val * 60)
            except Exception:
                pass
            self.config.set('require_2fa', require_2fa_var.get())
            # Add more config fields as needed (theme, etc.)

            # Save user profile fields
            if username:
                user_data = user_profile['user_data'] if user_profile and user_profile.get('user_data') else {}
                user_data['fullname'] = fullname_var.get()
                user_data['organization'] = org_var.get()
                self.auth_manager.update_user_profile(
                    username,
                    email=email_var.get(),
                    mobile_number=mobile_var.get(),
                    user_data=user_data
                )
            messagebox.showinfo("Settings Saved", "Your settings have been saved successfully.")

        ttk.Button(button_frame, text="💾 Save Settings", command=save_settings, style='success.TButton').pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="❌ Cancel", command=settings_window.destroy, style='danger.TButton').pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="🔄 Reset to Defaults", command=reset_to_defaults, style='info.TButton').pack(side=tk.LEFT)
    
    def show_help_dialog(self):
        """Show help dialog with navigation, search, and improved layout"""
        help_window = tk.Toplevel(self.root)
        help_window.title("IronLock Vault - Help")
        help_window.geometry("900x650")
        help_window.transient(self.root)
        help_window.resizable(True, True)
        help_window.grab_set()
        help_window.focus_set()
        help_window.attributes('-topmost', True)

        # Center window
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - 450
        y = (help_window.winfo_screenheight() // 2) - 325
        help_window.geometry(f'900x650+{x}+{y}')

        # Main container
        main_container = ttk.Frame(help_window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # --- Left Navigation Panel ---
        nav_frame = ttk.Frame(main_container, width=200)
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 0), pady=20)
        nav_frame.pack_propagate(False)
        nav_label = ttk.Label(nav_frame, text="Sections", font=('Arial', 12, 'bold'))
        nav_label.pack(anchor=tk.NW, pady=(0, 10))
        nav_items = [
            ("Overview", "OVERVIEW"),
            ("Security Features", "SECURITY FEATURES"),
            ("Getting Started", "GETTING STARTED"),
            ("Managing Vault Items", "MANAGING VAULT ITEMS"),
            ("QR Code Scanning", "QR CODE SCANNING"),
            ("Search & Filter", "SEARCH AND FILTER"),
            ("Settings", "SETTINGS AND CUSTOMIZATION"),
            ("Monitoring & Logs", "MONITORING AND LOGS"),
            ("Keyboard Shortcuts", "KEYBOARD SHORTCUTS"),
            ("Mouse Controls", "MOUSE CONTROLS"),
            ("Troubleshooting", "TROUBLESHOOTING"),
            ("Support", "SUPPORT"),
            ("Security Best Practices", "SECURITY BEST PRACTICES"),
            ("Important Notes", "IMPORTANT NOTES"),
            ("Tips", "TIPS FOR EFFICIENT USE"),
        ]
        # --- Search Bar ---
        search_var = tk.StringVar()
        search_entry = ttk.Entry(nav_frame, textvariable=search_var, width=18)
        search_entry.pack(anchor=tk.NW, pady=(10, 10))
        search_entry.insert(0, "Search help...")
        def clear_search(event):
            if search_entry.get() == "Search help...":
                search_entry.delete(0, tk.END)
        search_entry.bind('<FocusIn>', clear_search)

        # --- Help Content (Scrollable) ---
        content_frame = ttk.Frame(main_container)
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 20), pady=20)
        canvas = tk.Canvas(content_frame, borderwidth=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Section Anchors ---
        section_labels = {}
        def add_section(title, icon=None):
            anchor = title.upper()
            label = ttk.Label(scrollable_frame, text=f"{icon+' ' if icon else ''}{title}", font=('Arial', 15, 'bold'))
            label.pack(anchor=tk.W, pady=(30, 8))
            section_labels[anchor] = label
            ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 12))

        # --- Help Content (with anchors for navigation) ---
        help_sections = [
            ("Overview", "📋", "IronLock Vault is a secure desktop application that allows you to store and manage sensitive files, folders, and applications with military-grade encryption and two-factor authentication."),
            ("Security Features", "🔐", "• AES-256 Encryption: All data is encrypted using industry-standard AES-256 encryption\n• Two-Factor Authentication (2FA): Multiple authentication methods including TOTP and email OTP\n• Auto-Lock: Automatic vault locking after inactivity\n• Access Logging: Complete audit trail of all vault activities\n• Secure Key Management: Encryption keys are never stored in plain text"),
            ("Getting Started", "🚀", "1. Registration: Create a new account with username and password\n2. 2FA Setup: Configure two-factor authentication for enhanced security\n3. Adding Items: Use the left panel to add files, folders, or applications\n4. Accessing Items: Double-click items or use the context menu to access them"),
            ("Managing Vault Items", "📁", "• Add Application: Store executable files (.exe) securely\n• Add Folder: Encrypt entire folders and their contents\n• Add File: Secure any type of file with encryption\n• QR Code Scanner: Scan QR codes from camera, files, or clipboard\n• Search: Use the search bar to quickly find items\n• Context Menu: Right-click items for additional options"),
            ("QR Code Scanning", "📱", "• Camera Scan: Use your computer's camera to scan QR codes\n• File Upload: Select an image file containing a QR code\n• Clipboard: Scan QR codes copied to your clipboard\n• Screenshot: Take a screenshot and scan for QR codes\n• External Apps: Open external QR scanner applications\n• Auto-Detection: Automatically detects URLs, 2FA codes, and text\n• Vault Integration: Automatically add scanned data to your vault\n• QR Generation: Create QR codes for text, URLs, WiFi, contacts, and more\n• Save QR Codes: Save generated QR codes as PNG images"),
            ("Search & Filter", "🔍", "• Real-time Search: Type in the search bar for instant results\n• Advanced Search: Use the search dialog for detailed queries\n• QR Code Scanning: Scan QR codes from multiple sources\n• Filter Logs: Filter access logs by status (Success/Failed)\n• Sort Items: Click column headers to sort items"),
            ("Settings", "⚙️", "• Auto-Lock Timeout: Set inactivity timeout (0 to disable)\n• Theme Selection: Choose from multiple UI themes\n• 2FA Requirements: Configure 2FA for different actions\n• Log Level: Adjust logging verbosity"),
            ("Monitoring & Logs", "📊", "• Access Logs: View detailed access history\n• Statistics: Monitor vault usage and item counts\n• Security Events: Track failed access attempts\n• Activity Timeline: See when items were accessed"),
            ("Keyboard Shortcuts", "⌨️", "• Ctrl+Shift+L: Quick lock vault\n• Enter: Login/Confirm actions\n• Double-click: Access selected item\n• Right-click: Context menu\n• Mouse Wheel: Scroll through lists\n• Shift+Mouse Wheel: Horizontal scrolling"),
            ("Mouse Controls", "🖱️", "• Mouse Wheel: Vertical scrolling in all lists and dialogs\n• Shift+Mouse Wheel: Horizontal scrolling\n• Right-click: Context menus for items\n• Double-click: Access items or confirm selections"),
            ("Troubleshooting", "🔧", "• Forgot Password: Contact administrator for password reset\n• 2FA Issues: Use backup codes or email recovery\n• Locked Out: Wait for auto-lock timeout or restart application\n• Performance: Close unnecessary applications to improve speed"),
            ("Support", "📞", "For technical support or security concerns:\n• Check the logs for detailed error information\n• Review the settings for configuration issues\n• Contact your system administrator"),
            ("Security Best Practices", "🔒", "• Use strong, unique passwords\n• Enable 2FA for all accounts\n• Regularly update your password\n• Don't share your 2FA codes\n• Lock the vault when leaving your computer\n• Monitor access logs regularly\n• Keep the application updated"),
            ("Important Notes", "⚠️", "• Never share your master password\n• Keep your 2FA device secure\n• Regular backups are recommended\n• The vault is only as secure as your password\n• Auto-lock helps protect against unauthorized access\n• All access attempts are logged for security"),
            ("Tips", "🎯", "• Use descriptive names for your items\n• Organize items by creating folders\n• Use the search function to find items quickly\n• Set appropriate auto-lock timeout\n• Regularly review and clean up old items\n• Monitor your access patterns in the logs"),
        ]
        section_widgets = {}
        for title, icon, content in help_sections:
            add_section(title, icon)
            text = tk.Text(scrollable_frame, wrap=tk.WORD, font=('Consolas', 10), bg='white', fg='black', height=6, padx=15, pady=8, borderwidth=0, highlightthickness=0)
            text.insert(tk.END, content)
            text.config(state=tk.DISABLED)
            text.pack(fill=tk.X, expand=False, pady=(0, 0))
            section_widgets[title.upper()] = text

        # --- Navigation click: scroll to section ---
        def scroll_to_section(anchor):
            label = section_labels.get(anchor)
            if label:
                canvas.yview_moveto(label.winfo_y() / max(1, scrollable_frame.winfo_height()))
        for nav, anchor in nav_items:
            btn = ttk.Button(nav_frame, text=nav, style='secondary.TButton', width=20, command=lambda a=anchor: scroll_to_section(a))
            btn.pack(anchor=tk.NW, pady=2, fill=tk.X)

        # --- Search filter ---
        def filter_help(*args):
            query = search_var.get().strip().lower()
            for title, icon, content in help_sections:
                widget = section_widgets[title.upper()]
                if not query or query in content.lower() or query in title.lower():
                    widget.master.pack_configure()
                    widget.pack_configure()
                else:
                    widget.pack_forget()
        search_var.trace_add('write', filter_help)

        # --- Close button ---
        ttk.Button(content_frame, text="Close", command=help_window.destroy, style='primary.TButton').pack(pady=(10, 0), anchor=tk.SE, side=tk.BOTTOM)
    
    def show_qr_scan_dialog(self):
        """Show QR code scanner dialog"""
        def on_qr_scan_result(data):
            """Handle QR scan result"""
            if data:
                # Show result dialog
                result_window = tk.Toplevel(self.root)
                result_window.title("QR Code Scan Result")
                result_window.geometry("500x400")
                result_window.transient(self.root)
                result_window.grab_set()
                
                # Center window
                result_window.update_idletasks()
                x = (result_window.winfo_screenwidth() // 2) - 250
                y = (result_window.winfo_screenheight() // 2) - 200
                result_window.geometry(f'500x400+{x}+{y}')
                
                # Main frame
                main_frame = ttk.Frame(result_window)
                main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
                
                # Title
                ttk.Label(main_frame, text="📱 QR Code Scan Result", 
                         font=('Arial', 16, 'bold')).pack(pady=(0, 20))
                
                # Data display
                data_frame = ttk.LabelFrame(main_frame, text="Scanned Data", padding=15)
                data_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
                
                # Text widget for data
                text_widget = tk.Text(data_frame, wrap=tk.WORD, font=('Consolas', 10),
                                     bg='white', fg='black', height=10)
                text_widget.pack(fill=BOTH, expand=True)
                text_widget.insert(tk.END, data)
                text_widget.config(state=tk.DISABLED)
                
                # Action buttons frame
                actions_frame = ttk.Frame(main_frame)
                actions_frame.pack(fill=X, pady=(0, 10))
                
                # Copy button
                def copy_data():
                    result_window.clipboard_clear()
                    result_window.clipboard_append(data)
                    messagebox.showinfo("Copied", "Data copied to clipboard!")
                
                ttk.Button(actions_frame, text="📋 Copy Data", 
                          command=copy_data, style='info.TButton').pack(side=LEFT, padx=(0, 10))
                
                # Add to vault button
                def add_to_vault():
                    # Determine if it's a URL, text, or other data
                    if data.startswith(('http://', 'https://', 'ftp://')):
                        item_type = 'url'
                    elif data.startswith('otpauth://'):
                        item_type = '2fa'
                    else:
                        item_type = 'text'
                    
                    # Add to vault based on type
                    if item_type == 'url':
                        self.add_qr_url_to_vault(data)
                    elif item_type == '2fa':
                        self.add_qr_2fa_to_vault(data)
                    else:
                        self.add_qr_text_to_vault(data)
                    
                    result_window.destroy()
                
                ttk.Button(actions_frame, text="💾 Add to Vault", 
                          command=add_to_vault, style='success.TButton').pack(side=LEFT, padx=(0, 10))
                
                # Control buttons frame
                control_frame = ttk.Frame(main_frame)
                control_frame.pack(fill=X, pady=(10, 0))
                
                # Left side - Window control buttons
                window_controls = ttk.Frame(control_frame)
                window_controls.pack(side=tk.LEFT)
                
                # Minimize button
                def minimize_window():
                    result_window.iconify()
                ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
                
                # Maximize/Restore button
                is_maximized = False
                def toggle_maximize():
                    nonlocal is_maximized
                    if is_maximized:
                        result_window.geometry("500x400")
                        is_maximized = False
                    else:
                        result_window.state('zoomed')
                        is_maximized = True
                ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
                
                # Right side - Close button
                ttk.Button(control_frame, text="❌ Close", 
                          command=result_window.destroy, style='danger.TButton').pack(side=tk.RIGHT)
                
                # Handle window close event
                def on_result_close():
                    result_window.destroy()
                
                result_window.protocol("WM_DELETE_WINDOW", on_result_close)
        
        # Show QR scanner dialog
        if self.qr_scanner is None:
            messagebox.showerror("Error", "QR scanning is not available. Please install required dependencies.")
            return
        
        if QR_SCANNER_AVAILABLE:
            qr_scanner_ui = QRScannerUI(self.root, self.qr_scanner, on_qr_scan_result)
        elif WEB_QR_SCANNER_AVAILABLE:
            qr_scanner_ui = WebQRScannerUI(self.root, self.qr_scanner, on_qr_scan_result)
        else:
            messagebox.showerror("Error", "No QR scanner available.")
            return
            
        qr_scanner_ui.show_scan_dialog()
    
    def add_qr_url_to_vault(self, url):
        """Add scanned URL to vault"""
        try:
            # Extract domain name for item name
            from urllib.parse import urlparse
            parsed = urlparse(url)
            name = parsed.netloc or "URL"
            
            # Add as a text file with URL content
            item_data = {
                'name': f"URL - {name}",
                'type': 'file',
                'content': url,
                'description': f"URL scanned from QR code: {url}"
            }
            
            self.vault_manager.add_item(self.current_user, item_data)
            self.refresh_vault_items()
            messagebox.showinfo("Success", f"URL added to vault: {name}")
            
        except Exception as e:
            self.logger.log_error(f"Error adding URL to vault: {str(e)}")
            messagebox.showerror("Error", f"Failed to add URL to vault: {str(e)}")
    
    def add_qr_2fa_to_vault(self, otp_uri):
        """Add scanned 2FA URI to vault"""
        try:
            # Parse OTP URI
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(otp_uri)
            params = parse_qs(parsed.query)
            
            # Extract information
            issuer = params.get('issuer', ['Unknown'])[0]
            account = params.get('account', ['Unknown'])[0]
            secret = parsed.path.split('/')[-1] if parsed.path else 'Unknown'
            
            name = f"2FA - {issuer} ({account})"
            
            # Add as a text file with 2FA information
            item_data = {
                'name': name,
                'type': 'file',
                'content': f"OTP URI: {otp_uri}\nIssuer: {issuer}\nAccount: {account}\nSecret: {secret}",
                'description': f"2FA setup scanned from QR code for {issuer}"
            }
            
            self.vault_manager.add_item(self.current_user, item_data)
            self.refresh_vault_items()
            messagebox.showinfo("Success", f"2FA setup added to vault: {name}")
            
        except Exception as e:
            self.logger.log_error(f"Error adding 2FA to vault: {str(e)}")
            messagebox.showerror("Error", f"Failed to add 2FA to vault: {str(e)}")
    
    def add_qr_text_to_vault(self, text):
        """Add scanned text to vault"""
        try:
            # Create a name from the first line or first 30 characters
            lines = text.strip().split('\n')
            first_line = lines[0] if lines else "QR Text"
            name = first_line[:30] + "..." if len(first_line) > 30 else first_line
            
            # Add as a text file
            item_data = {
                'name': f"QR Text - {name}",
                'type': 'file',
                'content': text,
                'description': f"Text scanned from QR code"
            }
            
            self.vault_manager.add_item(self.current_user, item_data)
            self.refresh_vault_items()
            messagebox.showinfo("Success", f"Text added to vault: {name}")
            
        except Exception as e:
            self.logger.log_error(f"Error adding text to vault: {str(e)}")
            messagebox.showerror("Error", f"Failed to add text to vault: {str(e)}")
    
    def show_qr_generate_dialog(self):
        """Show QR code generation dialog"""
        generate_window = tk.Toplevel(self.root)
        generate_window.title("QR Code Generator")
        generate_window.geometry("500x600")
        generate_window.transient(self.root)
        generate_window.grab_set()
        
        # Center window
        generate_window.update_idletasks()
        x = (generate_window.winfo_screenwidth() // 2) - 250
        y = (generate_window.winfo_screenheight() // 2) - 300
        generate_window.geometry(f'500x600+{x}+{y}')
        
        # Main frame
        main_frame = ttk.Frame(generate_window)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Title
        ttk.Label(main_frame, text="🔲 QR Code Generator", 
                 font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Input Data", padding=15)
        input_frame.pack(fill=X, pady=(0, 20))
        
        # Data type selection
        ttk.Label(input_frame, text="Data Type:").pack(anchor=W, pady=(0, 5))
        data_type_var = tk.StringVar(value="text")
        data_type_combo = ttk.Combobox(input_frame, textvariable=data_type_var, 
                                      values=["Text", "URL", "WiFi", "Contact", "Email", "Phone"], 
                                      state="readonly", font=('Arial', 10))
        data_type_combo.pack(fill=X, pady=(0, 15))
        
        # Data input
        ttk.Label(input_frame, text="Data:").pack(anchor=W, pady=(0, 5))
        data_text = tk.Text(input_frame, height=6, font=('Arial', 10))
        data_text.pack(fill=X, pady=(0, 10))
        
        # Example button
        def show_example():
            data_type = data_type_var.get().lower()
            if data_type == "text":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "Hello World! This is a sample QR code.")
            elif data_type == "url":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "https://www.example.com")
            elif data_type == "wifi":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "WIFI:S:MyWiFi;T:WPA;P:mypassword123;;")
            elif data_type == "contact":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "BEGIN:VCARD\nVERSION:3.0\nFN:John Doe\nTEL:+1234567890\nEMAIL:john@example.com\nEND:VCARD")
            elif data_type == "email":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "mailto:john@example.com?subject=Hello&body=This is a test email")
            elif data_type == "phone":
                data_text.delete(1.0, tk.END)
                data_text.insert(1.0, "tel:+1234567890")
        
        ttk.Button(input_frame, text="📝 Show Example", 
                  command=show_example, style='secondary.TButton').pack(anchor=W)
        
        # QR code display frame
        qr_frame = ttk.LabelFrame(main_frame, text="Generated QR Code", padding=15)
        qr_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # QR code label (will be updated)
        qr_label = ttk.Label(qr_frame, text="Enter data and click 'Generate QR Code'")
        qr_label.pack(expand=True)
        
        # Generate function
        def generate_qr():
            data = data_text.get(1.0, tk.END).strip()
            if not data:
                messagebox.showwarning("Warning", "Please enter some data to encode.")
                return
            
            try:
                # Generate QR code
                qr_image = self.qr_scanner.generate_qr_code(data)
                if qr_image:
                    # Convert to PhotoImage for display
                    qr_image = qr_image.resize((200, 200), Image.Resampling.LANCZOS)
                    qr_photo = ImageTk.PhotoImage(qr_image)
                    
                    # Update label
                    qr_label.config(image=qr_photo, text="")
                    qr_label.image = qr_photo  # Keep a reference
                    
                    # Enable save button
                    save_btn.config(state="normal")
                    
            except Exception as e:
                self.logger.log_error(f"Error generating QR code: {str(e)}")
                messagebox.showerror("Error", f"Failed to generate QR code: {str(e)}")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=X, pady=(0, 10))
        
        # Generate button
        ttk.Button(buttons_frame, text="🔲 Generate QR Code", 
                  command=generate_qr, style='success.TButton').pack(side=LEFT, padx=(0, 10))
        
        # Save button
        def save_qr():
            data = data_text.get(1.0, tk.END).strip()
            if not data:
                messagebox.showwarning("Warning", "Please generate a QR code first.")
                return
            
            filename = filedialog.asksaveasfilename(
                title="Save QR Code",
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            
            if filename:
                try:
                    qr_image = self.qr_scanner.generate_qr_code(data, filename)
                    if qr_image:
                        messagebox.showinfo("Success", f"QR code saved to: {filename}")
                except Exception as e:
                    self.logger.log_error(f"Error saving QR code: {str(e)}")
                    messagebox.showerror("Error", f"Failed to save QR code: {str(e)}")
        
        save_btn = ttk.Button(buttons_frame, text="💾 Save QR Code", 
                             command=save_qr, style='info.TButton', state="disabled")
        save_btn.pack(side=LEFT, padx=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=X, pady=(10, 0))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            generate_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                generate_window.geometry("500x600")
                is_maximized = False
            else:
                generate_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Close button
        ttk.Button(control_frame, text="❌ Close", 
                  command=generate_window.destroy, style='danger.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_generate_close():
            generate_window.destroy()
        
        generate_window.protocol("WM_DELETE_WINDOW", on_generate_close)
    
    def lock_vault(self):
        """Lock the vault"""
        if messagebox.askyesno("Lock Vault", "Are you sure you want to lock the vault?"):
            self.is_logged_in = False
            self.current_user = None
            # Reset encryption
            self.vault_manager.encryption_manager.key = None
            self.vault_manager.encryption_manager.fernet = None
            self.auth_manager.logout()
            self.logger.log_info("Vault locked by user")
            self.setup_login_ui()
    
    def auto_lock(self):
        """Auto-lock the vault due to inactivity"""
        self.is_logged_in = False
        self.current_user = None
        # Reset encryption
        self.vault_manager.encryption_manager.key = None
        self.vault_manager.encryption_manager.fernet = None
        self.auth_manager.logout()
        self.logger.log_warning("Vault auto-locked due to inactivity")
        messagebox.showwarning("Auto-Lock", "Vault has been locked due to inactivity")
        self.setup_login_ui()
    
    def show_first_time_setup_wizard(self):
        """Show comprehensive first-time setup wizard"""
        # Clear window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="🚀 Welcome to IronLock Vault", 
            font=('Arial', 24, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Let's set up your secure vault account",
            font=('Arial', 12),
            foreground='gray'
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Progress indicator
        self.setup_step = 1
        self.total_steps = 4
        progress_label = ttk.Label(
            main_frame,
            text=f"Step {self.setup_step} of {self.total_steps}",
            font=('Arial', 10),
            foreground='blue'
        )
        progress_label.pack(pady=(0, 20))
        
        # Content frame
        self.content_frame = ttk.Frame(main_frame)
        self.content_frame.pack(fill=BOTH, expand=True, pady=20)
        
        # Navigation frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=X, pady=20)
        
        self.back_btn = ttk.Button(
            nav_frame,
            text="← Back",
            command=self.previous_setup_step,
            state='disabled'
        )
        self.back_btn.pack(side=LEFT, padx=(0, 10))
        
        self.next_btn = ttk.Button(
            nav_frame,
            text="Next →",
            command=self.next_setup_step,
            style='success.TButton'
        )
        self.next_btn.pack(side=RIGHT)
        
        # Store references
        self.progress_label = progress_label
        self.nav_frame = nav_frame
        
        # Show first step
        self.show_setup_step(1)
    
    def show_setup_step(self, step):
        """Show specific setup step"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        self.setup_step = step
        self.progress_label.config(text=f"Step {step} of {self.total_steps}")
        
        if step == 1:
            self.show_account_creation_step()
        elif step == 2:
            self.show_2fa_setup_step()
        elif step == 3:
            self.show_security_settings_step()
        elif step == 4:
            self.show_completion_step()
    
    def show_account_creation_step(self):
        """Step 1: Account creation"""
        # Welcome message
        welcome_frame = ttk.LabelFrame(self.content_frame, text="Create Your Account", padding=20)
        welcome_frame.pack(fill=X, pady=10)
        
        ttk.Label(
            welcome_frame,
            text="Welcome to IronLock Vault! Let's create your secure account.",
            font=('Arial', 11)
        ).pack(pady=(0, 20))
        
        # Account form
        form_frame = ttk.Frame(welcome_frame)
        form_frame.pack(fill=X)
        
        # Username
        ttk.Label(form_frame, text="Username:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=(0, 5))
        self.setup_username_entry = ttk.Entry(form_frame, font=('Arial', 12))
        self.setup_username_entry.pack(fill=X, pady=(0, 15))
        ttk.Label(form_frame, text="Choose a unique username (3-20 characters, letters and numbers only)", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Password
        self.setup_password_entry, self.setup_password_show_btn, setup_password_field = self.create_password_field(
            form_frame, 
            show_label=True, 
            label_text="Password:"
        )
        setup_password_field.pack(fill=X, pady=(15, 5))
        
        # Confirm password
        self.setup_confirm_password_entry, self.setup_confirm_show_btn, setup_confirm_field = self.create_password_field(
            form_frame, 
            show_label=True, 
            label_text="Confirm Password:"
        )
        setup_confirm_field.pack(fill=X, pady=(15, 15))
        
        # Password strength indicator
        self.setup_strength_label = ttk.Label(form_frame, text="Password strength: ", 
                                            font=('Arial', 9), foreground='gray')
        self.setup_strength_label.pack(anchor=W)
        
        # Email (optional)
        ttk.Label(form_frame, text="Email (Optional):", font=('Arial', 10, 'bold')).pack(anchor=W, pady=(15, 5))
        self.setup_email_entry = ttk.Entry(form_frame, font=('Arial', 12))
        self.setup_email_entry.pack(fill=X, pady=(0, 5))
        ttk.Label(form_frame, text="Used for password recovery and security alerts", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Mobile Number (optional)
        ttk.Label(form_frame, text="Mobile Number (Optional):", font=('Arial', 10, 'bold')).pack(anchor=W, pady=(15, 5))
        self.setup_mobile_entry = ttk.Entry(form_frame, font=('Arial', 12))
        self.setup_mobile_entry.pack(fill=X, pady=(0, 5))
        ttk.Label(form_frame, text="Format: +1 (555) 123-4567 or 5551234567", 
                 font=('Arial', 9), foreground='gray').pack(anchor=W)
        
        # Bind password strength check
        self.setup_password_entry.bind('<KeyRelease>', self.check_setup_password_strength)
        self.setup_confirm_password_entry.bind('<KeyRelease>', self.check_setup_password_strength)
        
        # Update navigation
        self.next_btn.config(text="Next →", command=self.next_setup_step)
        self.back_btn.config(state='disabled')
    
    def show_2fa_setup_step(self):
        """Step 2: 2FA setup"""
        # 2FA setup frame
        tfa_frame = ttk.LabelFrame(self.content_frame, text="Two-Factor Authentication Setup", padding=20)
        tfa_frame.pack(fill=X, pady=10)
        
        ttk.Label(
            tfa_frame,
            text="Enhance your security with two-factor authentication (2FA).",
            font=('Arial', 11)
        ).pack(pady=(0, 20))
        
        # 2FA options
        options_frame = ttk.Frame(tfa_frame)
        options_frame.pack(fill=X)
        
        # TOTP option
        totp_frame = ttk.LabelFrame(options_frame, text="Google Authenticator / TOTP", padding=15)
        totp_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            totp_frame,
            text="Use Google Authenticator or any TOTP app to generate time-based codes.",
            font=('Arial', 10)
        ).pack(pady=(0, 10))
        
        self.totp_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            totp_frame,
            text="Enable TOTP (Recommended)",
            variable=self.totp_var,
            command=self.update_2fa_options
        ).pack(anchor=W)
        
        # Email OTP option
        email_frame = ttk.LabelFrame(options_frame, text="Email OTP", padding=15)
        email_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            email_frame,
            text="Receive one-time codes via email for additional security.",
            font=('Arial', 10)
        ).pack(pady=(0, 10))
        
        self.email_otp_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            email_frame,
            text="Enable Email OTP",
            variable=self.email_otp_var,
            command=self.update_2fa_options
        ).pack(anchor=W)
        
        # Security note
        security_frame = ttk.LabelFrame(tfa_frame, text="Security Information", padding=15)
        security_frame.pack(fill=X, pady=(15, 0))
        
        ttk.Label(
            security_frame,
            text="• TOTP codes change every 30 seconds\n• Email OTP codes expire after 5 minutes\n• You can enable both methods for maximum security\n• You can change these settings later in the app",
            font=('Arial', 9),
            justify=LEFT
        ).pack(anchor=W)
        
        # Update navigation
        self.next_btn.config(text="Next →", command=self.next_setup_step)
        self.back_btn.config(state='normal', command=self.previous_setup_step)
    
    def show_security_settings_step(self):
        """Step 3: Security settings"""
        # Security settings frame
        security_frame = ttk.LabelFrame(self.content_frame, text="Security Settings", padding=20)
        security_frame.pack(fill=X, pady=10)
        
        ttk.Label(
            security_frame,
            text="Configure additional security settings for your vault.",
            font=('Arial', 11)
        ).pack(pady=(0, 20))
        
        # Auto-lock settings
        autolock_frame = ttk.LabelFrame(security_frame, text="Auto-Lock Settings", padding=15)
        autolock_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            autolock_frame,
            text="Automatically lock the vault after inactivity:",
            font=('Arial', 10)
        ).pack(pady=(0, 10))
        
        self.auto_lock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            autolock_frame,
            text="Enable auto-lock",
            variable=self.auto_lock_var
        ).pack(anchor=W)
        
        # Auto-lock timeout
        timeout_frame = ttk.Frame(autolock_frame)
        timeout_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Label(timeout_frame, text="Lock after:").pack(side=LEFT)
        self.timeout_var = tk.StringVar(value="5")
        timeout_combo = ttk.Combobox(
            timeout_frame,
            textvariable=self.timeout_var,
            values=["1", "3", "5", "10", "15", "30"],
            state="readonly",
            width=10
        )
        timeout_combo.pack(side=LEFT, padx=(5, 5))
        ttk.Label(timeout_frame, text="minutes of inactivity").pack(side=LEFT)
        
        # Backup settings
        backup_frame = ttk.LabelFrame(security_frame, text="Backup Settings", padding=15)
        backup_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            backup_frame,
            text="Configure automatic backup of your vault data:",
            font=('Arial', 10)
        ).pack(pady=(0, 10))
        
        self.backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            backup_frame,
            text="Enable automatic backups",
            variable=self.backup_var
        ).pack(anchor=W)
        
        # Theme selection
        theme_frame = ttk.LabelFrame(security_frame, text="Appearance", padding=15)
        theme_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            theme_frame,
            text="Choose your preferred theme:",
            font=('Arial', 10)
        ).pack(pady=(0, 10))
        
        self.theme_var = tk.StringVar(value="darkly")
        theme_combo = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=["darkly", "cosmo", "flatly", "journal", "litera", "lumen", "minty", "pulse", "sandstone", "simplex", "sketchy", "spacelab", "united", "yeti"],
            state="readonly",
            width=15
        )
        theme_combo.pack(anchor=W)
        
        # Update navigation
        self.next_btn.config(text="Next →", command=self.next_setup_step)
        self.back_btn.config(state='normal', command=self.previous_setup_step)
    
    def show_completion_step(self):
        """Step 4: Setup completion"""
        # Completion frame
        completion_frame = ttk.LabelFrame(self.content_frame, text="Setup Complete", padding=20)
        completion_frame.pack(fill=X, pady=10)
        
        # Success message
        ttk.Label(
            completion_frame,
            text="🎉 Congratulations! Your IronLock Vault is ready.",
            font=('Arial', 14, 'bold')
        ).pack(pady=(0, 20))
        
        # Summary
        summary_frame = ttk.Frame(completion_frame)
        summary_frame.pack(fill=X, pady=(0, 20))
        
        ttk.Label(
            summary_frame,
            text="Your account has been created with the following security features:",
            font=('Arial', 11)
        ).pack(pady=(0, 15))
        
        # Features list
        features = [
            "✓ Strong password protection",
            "✓ Two-factor authentication (TOTP)",
            "✓ Email OTP (if enabled)",
            "✓ Auto-lock protection",
            "✓ Encrypted vault storage",
            "✓ Activity logging"
        ]
        
        for feature in features:
            ttk.Label(
                summary_frame,
                text=feature,
                font=('Arial', 10)
            ).pack(anchor=W, pady=2)
        
        # Next steps
        next_steps_frame = ttk.LabelFrame(completion_frame, text="Next Steps", padding=15)
        next_steps_frame.pack(fill=X, pady=(20, 0))
        
        ttk.Label(
            next_steps_frame,
            text="1. You'll be redirected to the login screen\n2. Log in with your new credentials\n3. Set up your 2FA app (if enabled)\n4. Start adding your secure items to the vault",
            font=('Arial', 10),
            justify=LEFT
        ).pack(anchor=W)
        
        # Update navigation
        self.next_btn.config(text="Complete Setup", command=self.complete_setup)
        self.back_btn.config(state='normal', command=self.previous_setup_step)
    
    def check_setup_password_strength(self, event=None):
        """Check password strength during setup"""
        password = self.setup_password_entry.get()
        confirm = self.setup_confirm_password_entry.get()
        
        if len(password) == 0:
            self.setup_strength_label.config(text="Password strength: ", foreground='gray')
            return
        
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("At least 8 characters")
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            feedback.append("Uppercase letter")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            feedback.append("Lowercase letter")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            feedback.append("Number")
        
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        else:
            feedback.append("Special character")
        
        # Update strength indicator
        if score <= 2:
            color = 'red'
            strength = 'Weak'
        elif score <= 3:
            color = 'orange'
            strength = 'Fair'
        elif score <= 4:
            color = 'blue'
            strength = 'Good'
        else:
            color = 'green'
            strength = 'Strong'
        
        self.setup_strength_label.config(text=f"Password strength: {strength}", foreground=color)
        
        # Check if passwords match
        if confirm and password != confirm:
            self.setup_strength_label.config(text="Passwords do not match!", foreground='red')
    
    def update_2fa_options(self):
        """Update 2FA options based on selections"""
        # This method can be used to enable/disable options based on selections
        pass
    
    def next_setup_step(self):
        """Move to next setup step"""
        if self.setup_step == 1:
            # Validate account creation
            if not self.validate_account_creation():
                return
        elif self.setup_step == 2:
            # Validate 2FA setup
            if not self.validate_2fa_setup():
                return
        elif self.setup_step == 3:
            # Validate security settings
            if not self.validate_security_settings():
                return
        
        if self.setup_step < self.total_steps:
            self.show_setup_step(self.setup_step + 1)
    
    def previous_setup_step(self):
        """Move to previous setup step"""
        if self.setup_step > 1:
            self.show_setup_step(self.setup_step - 1)
    
    def validate_account_creation(self):
        """Validate account creation step"""
        username = self.setup_username_entry.get().strip()
        password = self.setup_password_entry.get()
        confirm = self.setup_confirm_password_entry.get()
        email = self.setup_email_entry.get().strip()
        mobile_number = self.setup_mobile_entry.get().strip()
        
        # Validate username
        if not username:
            messagebox.showerror("Error", "Please enter a username.")
            return False
        
        if len(username) < 3 or len(username) > 20:
            messagebox.showerror("Error", "Username must be 3-20 characters long.")
            return False
        
        if not username.replace('_', '').replace('-', '').isalnum():
            messagebox.showerror("Error", "Username can only contain letters, numbers, underscores, and hyphens.")
            return False
        
        # Validate password
        if not password:
            messagebox.showerror("Error", "Please enter a password.")
            return False
        
        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters long.")
            return False
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match.")
            return False
        
        # Validate email (optional)
        if email and '@' not in email:
            messagebox.showerror("Error", "Please enter a valid email address.")
            return False
        
        # Validate mobile number (optional)
        if mobile_number:
            is_valid, mobile_error = self.auth_manager.validate_mobile_number(mobile_number)
            if not is_valid:
                messagebox.showerror("Error", mobile_error)
                return False
        
        return True
    
    def validate_2fa_setup(self):
        """Validate 2FA setup step"""
        # 2FA is optional - user can skip it
        if not self.totp_var.get() and not self.email_otp_var.get():
            # Show warning but allow to proceed
            result = messagebox.askyesno(
                "2FA Setup", 
                "You haven't selected any 2FA methods. This means your account will only be protected by your password.\n\n"
                "For enhanced security, we strongly recommend enabling at least one 2FA method.\n\n"
                "Do you want to continue without 2FA?"
            )
            if not result:
                return False
        
        return True
    
    def validate_security_settings(self):
        """Validate security settings step"""
        # All validations passed
        return True
    
    def complete_setup(self):
        """Complete the setup process"""
        try:
            # Get all the setup data
            username = self.setup_username_entry.get().strip()
            password = self.setup_password_entry.get()
            email = self.setup_email_entry.get().strip()
            mobile_number = self.setup_mobile_entry.get().strip()
        
            # Create user data
            user_data = {
                'setup_date': datetime.now().isoformat(),
                '2fa_totp_enabled': self.totp_var.get(),
                '2fa_email_enabled': self.email_otp_var.get(),
                'auto_lock_enabled': self.auto_lock_var.get(),
                'auto_lock_timeout': int(self.timeout_var.get()) * 60,  # Convert to seconds
                'backup_enabled': self.backup_var.get(),
                'theme': self.theme_var.get()
            }
            
            # Validate mobile number if provided
            if mobile_number:
                is_valid, mobile_error = self.auth_manager.validate_mobile_number(mobile_number)
                if not is_valid:
                    messagebox.showerror("Setup Error", mobile_error)
                    return
            
            # Check if 2FA is enabled
            enable_2fa = self.totp_var.get() or self.email_otp_var.get()
            
            # Register the user
            success, message = self.auth_manager.register_user(username, password, email, mobile_number, user_data, enable_2fa)
        
            if not success:
                messagebox.showerror("Registration Error", message)
                return
            
            # Update configuration
            self.config.set('auto_lock_timeout', user_data['auto_lock_timeout'])
            self.config.set('theme', user_data['theme'])
            self.config.set('backup_enabled', user_data['backup_enabled'])
            self.config.set('setup_complete', True)
            
            # Log the setup completion
            self.logger.log_info(f"First-time setup completed for user: {username}")
            
            # Show success message
            messagebox.showinfo(
                "Setup Complete", 
                f"Account created successfully!\n\nUsername: {username}\n\nYou can now log in to your vault."
            )
            
            # Return to login screen
            self.setup_login_ui()
            
        except Exception as e:
            self.logger.log_error(f"Setup completion error: {str(e)}")
            messagebox.showerror("Setup Error", f"An error occurred during setup: {str(e)}")
    
    def perform_password_change(self, current_password, new_password):
        """Perform the actual password change"""
        try:
            success, message = self.auth_manager.change_password(self.current_user, current_password, new_password)
            
            if success:
                messagebox.showinfo("Success", "Password changed successfully!")
                self.logger.log_info(f"Password changed for user: {self.current_user}")
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            self.logger.log_error(f"Password change error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while changing password: {str(e)}")
    
    def perform_profile_update(self, new_email, new_mobile, new_fullname, new_org):
        """Perform the actual profile update"""
        try:
            # Prepare user data
            user_data = {
                'fullname': new_fullname,
                'organization': new_org
            }
            
            success, message = self.auth_manager.update_user_profile(
                self.current_user, 
                email=new_email, 
                mobile_number=new_mobile, 
                user_data=user_data
            )
            
            if success:
                messagebox.showinfo("Success", "Profile updated successfully!")
                self.logger.log_info(f"Profile updated for user: {self.current_user}")
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            self.logger.log_error(f"Profile update error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred while updating profile: {str(e)}")

    def reset_totp_with_otp(self):
        """OTP-protected TOTP reset flow"""
        def on_success():
            # Generate new TOTP secret
            import pyotp
            new_secret = pyotp.random_base32()
            username = self.current_user
            try:
                # Update in database
                conn = self.auth_manager.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET totp_secret = ? WHERE username = ?", (new_secret, username))
                conn.commit()
                conn.close()
                # Update in current_user
                self.auth_manager.current_user['totp_secret'] = new_secret
                self.logger.log_info(f"TOTP reset for user: {username}")
                # Show QR code
                self.show_new_totp_qr(new_secret)
            except Exception as e:
                self.logger.log_error(f"TOTP reset error: {str(e)}")
                messagebox.showerror("Error", f"Failed to reset TOTP: {str(e)}")
        self.verify_otp_for_sensitive_action(on_success)

    def show_new_totp_qr(self, new_secret):
        """Show the new TOTP QR code for the user to scan"""
        import pyotp
        import qrcode
        username = self.current_user
        issuer = self.config.get('totp_issuer', 'IronLock Vault')
        totp_uri = pyotp.totp.TOTP(new_secret).provisioning_uri(name=username, issuer_name=issuer)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Show in a dialog
        qr_window = tk.Toplevel(self.root)
        qr_window.title("Scan New Authenticator QR Code")
        qr_window.geometry("350x400")
        qr_window.transient(self.root)
        qr_window.grab_set()
        ttk.Label(qr_window, text="Scan this QR code in your authenticator app", font=('Arial', 12, 'bold')).pack(pady=(10, 10))
        # Convert PIL image to Tkinter PhotoImage
        from PIL import ImageTk
        img = img.resize((250, 250))
        photo = ImageTk.PhotoImage(img)
        qr_label = ttk.Label(qr_window, image=photo)
        qr_label.image = photo
        qr_label.pack(pady=(0, 10))
        ttk.Label(qr_window, text=f"Secret: {new_secret}", font=('Arial', 10)).pack(pady=(0, 10))
        ttk.Label(qr_window, text="Your old authenticator app will no longer work.", font=('Arial', 9), foreground='red').pack(pady=(0, 10))
        
        # Control buttons frame
        control_frame = ttk.Frame(qr_window)
        control_frame.pack(fill=X, pady=(10, 10))
        
        # Left side - Window control buttons
        window_controls = ttk.Frame(control_frame)
        window_controls.pack(side=tk.LEFT)
        
        # Minimize button
        def minimize_window():
            qr_window.iconify()
        ttk.Button(window_controls, text="🗕 Minimize", command=minimize_window, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Maximize/Restore button
        is_maximized = False
        def toggle_maximize():
            nonlocal is_maximized
            if is_maximized:
                qr_window.geometry("350x400")
                is_maximized = False
            else:
                qr_window.state('zoomed')
                is_maximized = True
        ttk.Button(window_controls, text="🗗 Maximize", command=toggle_maximize, style='info.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Right side - Done button
        ttk.Button(control_frame, text="Done", command=qr_window.destroy, style='success.TButton').pack(side=tk.RIGHT)
        
        # Handle window close event
        def on_qr_close():
            qr_window.destroy()
        
        qr_window.protocol("WM_DELETE_WINDOW", on_qr_close)

    def on_treeview_click(self, event):
        # Identify if click is on the 'Select' column and toggle checkbox
        region = self.items_tree.identify('region', event.x, event.y)
        if region != 'cell':
            return
        col = self.items_tree.identify_column(event.x)
        if col != '#0':  # '#0' is the first column ('Select')
            return
        row_id = self.items_tree.identify_row(event.y)
        if not row_id:
            return
        item_tags = self.items_tree.item(row_id, 'tags')
        if not item_tags:
            return
        item_id = str(item_tags[0])
        all_items = self.items_tree.get_children()
        all_ids = set()
        for item in all_items:
            tags = self.items_tree.item(item, 'tags')
            if tags:
                all_ids.add(str(tags[0]))
        # If all are selected, clicking any should deselect all except the clicked one (and keep it checked)
        if self.selected_items == all_ids:
            self.selected_items = set([item_id])
        else:
            if item_id in self.selected_items:
                self.selected_items.remove(item_id)
            else:
                self.selected_items.add(item_id)
        self.refresh_vault_items()

    def show_splash_screen(self):
        splash = tk.Toplevel()
        splash.overrideredirect(True)
        splash.geometry("400x300")
        splash.configure(bg="#222831")
        # Center splash
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() // 2) - 200
        y = (splash.winfo_screenheight() // 2) - 150
        splash.geometry(f"400x300+{x}+{y}")
        # Logo or app name - centered vertically
        logo_frame = tk.Frame(splash, bg="#222831")
        logo_frame.pack(expand=True)
        # Placeholder for logo (use image if available)
        logo_label = tk.Label(logo_frame, text="🛡️", font=("Arial", 48), bg="#222831", fg="#00adb5")
        logo_label.pack(pady=(30, 10), anchor=tk.E, padx=(0, 20))
        name_label = tk.Label(logo_frame, text="IronLock Vault", font=("Arial", 22, "bold"), bg="#222831", fg="#eeeeee")
        name_label.pack(anchor=tk.W, padx=(20, 0), pady=(0, 10))
        # Loading animation
        loading_label = tk.Label(logo_frame, text="Loading...", font=("Arial", 12), bg="#222831", fg="#eeeeee")
        loading_label.pack(pady=(10, 0))
        # Animate dots using after (main thread)
        def animate(i=0):
            if i < 10:
                loading_label.config(text="Loading" + "." * (i % 4))
                splash.after(150, lambda: animate(i + 1))
            else:
                splash.destroy()
        self.root.withdraw()  # Hide main window during splash
        splash.after(100, animate)
        splash.wait_window()
        self.root.deiconify()  # Show main window after splash

    # --- Loading Spinner Dialog ---
    def show_loading(self, message="Loading..."):
        self.loading_win = tk.Toplevel(self.root)
        self.loading_win.title("")
        self.loading_win.geometry("300x120")
        self.loading_win.resizable(False, False)
        self.loading_win.transient(self.root)
        self.loading_win.grab_set()
        self.loading_win.overrideredirect(True)
        # Center
        self.loading_win.update_idletasks()
        x = (self.loading_win.winfo_screenwidth() // 2) - 150
        y = (self.loading_win.winfo_screenheight() // 2) - 60
        self.loading_win.geometry(f"300x120+{x}+{y}")
        frame = ttk.Frame(self.loading_win, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        label = ttk.Label(frame, text=message, font=("Arial", 12, "bold"))
        label.pack(pady=(10, 10))
        # Spinner (animated dots)
        spinner = ttk.Label(frame, text="● ● ●", font=("Arial", 24), foreground="#00adb5")
        spinner.pack()
        self._loading_running = True
        def animate():
            dots = ["●    ", "● ●  ", "● ● ●", "  ● ●", "    ●"]
            i = 0
            while self._loading_running:
                spinner.config(text=dots[i % len(dots)])
                self.loading_win.update()
                time.sleep(0.2)
                i += 1
        import threading
        self._loading_thread = threading.Thread(target=animate, daemon=True)
        self._loading_thread.start()
    def hide_loading(self):
        self._loading_running = False
        if hasattr(self, 'loading_win') and self.loading_win:
            self.loading_win.destroy()
            self.loading_win = None

    def setup_activity_tracking(self, widget):
        """Setup activity tracking for auto-lock functionality"""
        def on_activity(event=None):
            # Update the last activity time in the main application
            if self.app_instance and hasattr(self.app_instance, 'last_activity'):
                self.app_instance.last_activity = time.time()
                # Log activity occasionally (not on every event to avoid spam)
                if hasattr(self, '_last_activity_log') and time.time() - self._last_activity_log > 60:
                    self.logger.log_info("User activity detected - auto-lock timer reset")
                    self._last_activity_log = time.time()
                elif not hasattr(self, '_last_activity_log'):
                    self._last_activity_log = time.time()
        # Bind activity events to the widget and all its children
        widget.bind('<Motion>', on_activity)
        widget.bind('<Key>', on_activity)
        widget.bind('<Button>', on_activity)
        widget.bind('<MouseWheel>', on_activity)
        # Recursively bind to all child widgets
        for child in widget.winfo_children():
            try:
                child.bind('<Motion>', on_activity)
                child.bind('<Key>', on_activity)
                child.bind('<Button>', on_activity)
                child.bind('<MouseWheel>', on_activity)
            except Exception:
                pass  # Some widgets might not support all events
        self.logger.log_info("Activity tracking enabled for vault interface")

    def verify_integrity_selected_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to verify.")
            return
        item_id = self.items_tree.item(selection[0])['tags'][0]
        result = self.vault_manager.verify_item_integrity(item_id, self.current_user['username'])
        if result['status'] == 'OK':
            messagebox.showinfo("Integrity Check", f"File integrity verified.\nHash: {result['hash']}")
        else:
            messagebox.showerror("Integrity Check Failed", f"File integrity check failed!\nExpected: {result['expected']}\nActual: {result['actual']}")

    def show_versions_selected_item(self):
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to view versions.")
            return
        item_id = self.items_tree.item(selection[0])['tags'][0]
        versions = self.vault_manager.get_item_versions(item_id, self.current_user['username'])
        version_list = "\n".join([f"v{v['version']}: {v['added_date']}" for v in versions])
        messagebox.showinfo("File Versions", f"Available versions:\n{version_list}")
    
    def secure_delete_selected_item(self):
        """Securely delete the original file for selected item"""
        messagebox.showinfo("Secure Delete", "Secure delete feature coming soon!")
    
    def show_qr_code(self):
        """Show QR code for 2FA setup"""
        # This method should show the QR code for TOTP setup
        # For now, just show a placeholder message
        messagebox.showinfo("QR Code", "QR code setup feature coming soon!")
    
