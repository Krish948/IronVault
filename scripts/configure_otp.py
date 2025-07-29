#!/usr/bin/env python3
"""
OTP Configuration Script for IronLock Vault
Helps users configure email and SMS OTP delivery settings
"""

import json
import os
import sys
from pathlib import Path

def load_config():
    """Load current configuration"""
    config_file = "data/config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    """Save configuration to file"""
    config_file = "data/config.json"
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

def configure_email():
    """Configure email settings"""
    print("\n=== Email OTP Configuration ===")
    print("To enable email OTP delivery, you need to configure SMTP settings.")
    print("For Gmail, you'll need to:")
    print("1. Enable 2-factor authentication on your email provider (recommended)")
    print("2. Generate an App Password if required by your provider")
    print("3. Use the App Password instead of your regular password")
    print()
    
    smtp_server = input("SMTP Server (e.g., smtp.gmail.com): ").strip()
    smtp_port = input("SMTP Port (e.g., 587): ").strip()
    email_username = input("Email Address: ").strip()
    email_password = input("Email Password/App Password: ").strip()
    
    if smtp_server and smtp_port and email_username and email_password:
        return {
            'email_smtp_server': smtp_server,
            'email_smtp_port': int(smtp_port),
            'email_username': email_username,
            'email_password': email_password,
            'enable_email_alerts': True
        }
    return {}

def configure_sms():
    """Configure SMS settings"""
    print("\n=== SMS OTP Configuration ===")
    print("To enable SMS OTP delivery, you need a Twilio account:")
    print("1. Sign up at https://www.twilio.com")
    print("2. Get your Account SID and Auth Token")
    print("3. Get a Twilio phone number")
    print()
    
    account_sid = input("Twilio Account SID: ").strip()
    auth_token = input("Twilio Auth Token: ").strip()
    phone_number = input("Twilio Phone Number (+1234567890): ").strip()
    
    if account_sid and auth_token and phone_number:
        return {
            'twilio_account_sid': account_sid,
            'twilio_auth_token': auth_token,
            'twilio_phone_number': phone_number,
            'enable_sms_otp': True
        }
    return {}

def test_email_config(config):
    """Test email configuration"""
    print("\n=== Testing Email Configuration ===")
    test_email = input("Enter test email address: ").strip()
    
    if not test_email:
        print("No test email provided. Skipping test.")
        return
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = config['email_username']
        msg['To'] = test_email
        msg['Subject'] = "IronLock Vault - Email Test"
        
        body = "This is a test email from IronLock Vault. Email OTP is working correctly!"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(config['email_smtp_server'], config['email_smtp_port'])
        server.starttls()
        server.login(config['email_username'], config['email_password'])
        server.send_message(msg)
        server.quit()
        
        print("✅ Email test successful! Check your inbox.")
        
    except Exception as e:
        print(f"❌ Email test failed: {str(e)}")
        print("Please check your email settings and try again.")

def main():
    """Main configuration function"""
    print("IronLock Vault - OTP Configuration")
    print("==================================")
    
    # Load current config
    config = load_config()
    
    print("\nCurrent OTP Settings:")
    print(f"Email OTP: {'Enabled' if config.get('enable_email_alerts') else 'Disabled'}")
    print(f"SMS OTP: {'Enabled' if config.get('enable_sms_otp') else 'Disabled'}")
    
    while True:
        print("\nOptions:")
        print("1. Configure Email OTP")
        print("2. Configure SMS OTP")
        print("3. Test Email Configuration")
        print("4. View Current Settings")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            email_config = configure_email()
            if email_config:
                config.update(email_config)
                save_config(config)
                print("✅ Email configuration saved!")
            else:
                print("❌ Email configuration incomplete. Settings not saved.")
        
        elif choice == '2':
            sms_config = configure_sms()
            if sms_config:
                config.update(sms_config)
                save_config(config)
                print("✅ SMS configuration saved!")
            else:
                print("❌ SMS configuration incomplete. Settings not saved.")
        
        elif choice == '3':
            if config.get('enable_email_alerts') and config.get('email_username'):
                test_email_config(config)
            else:
                print("❌ Email not configured. Please configure email first.")
        
        elif choice == '4':
            print("\nCurrent Settings:")
            print(f"SMTP Server: {config.get('email_smtp_server', 'Not set')}")
            print(f"SMTP Port: {config.get('email_smtp_port', 'Not set')}")
            print(f"Email: {config.get('email_username', 'Not set')}")
            print(f"Email OTP: {'Enabled' if config.get('enable_email_alerts') else 'Disabled'}")
            print(f"Twilio Account SID: {config.get('twilio_account_sid', 'Not set')}")
            print(f"Twilio Phone: {config.get('twilio_phone_number', 'Not set')}")
            print(f"SMS OTP: {'Enabled' if config.get('enable_sms_otp') else 'Disabled'}")
        
        elif choice == '5':
            print("Configuration complete!")
            break
        
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main() 