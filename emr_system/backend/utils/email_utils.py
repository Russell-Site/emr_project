# ============================================================
# utils/email_utils.py - Email Sending Utilities
# Para sa pagpapadala ng OTP sa email ng Admin
# Gumagamit ng aiosmtplib para sa async email sending
# ============================================================

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Kunin ang SMTP settings mula sa environment variables
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", "noreply@district1health.gov.ph")


def send_otp_email(recipient_email: str, recipient_name: str, otp_code: str, purpose: str = "registration") -> bool:
    """
    Magpadala ng OTP sa email ng Admin.
    Ginagamit ito bago mag-finalize ng bagong BHW registration.
    
    Parameters:
        recipient_email: Email address ng tatanggap
        recipient_name: Pangalan ng tatanggap
        otp_code: Ang OTP na dapat ipadala
        purpose: Kung para saan ang OTP ('registration' o 'unlock')
    
    Returns True kung matagumpay, False kung may error.
    """
    try:
        # Gumawa ng email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"EMR System - Your OTP for {purpose.title()}"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = recipient_email

        # Depende sa purpose, iba ang nilalaman ng email
        if purpose == "registration":
            action_text = "register a new Barangay Health Worker (BHW) account"
        else:
            action_text = "perform this action"

        # HTML version ng email - mas maganda ang hitsura
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #0a4f76, #1a8a5e); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 24px; }}
                .header p {{ color: #cce5ff; margin: 5px 0 0; }}
                .body {{ padding: 30px; }}
                .otp-box {{ background: #f0f7ff; border: 2px solid #0a4f76; border-radius: 8px; text-align: center; padding: 20px; margin: 20px 0; }}
                .otp-code {{ font-size: 36px; font-weight: bold; color: #0a4f76; letter-spacing: 8px; }}
                .warning {{ color: #dc3545; font-size: 13px; margin-top: 15px; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 District 1 Health EMR System</h1>
                    <p>One-Time Password (OTP) Verification</p>
                </div>
                <div class="body">
                    <p>Dear <strong>{recipient_name}</strong>,</p>
                    <p>You have requested to <strong>{action_text}</strong>. 
                    Please use the OTP below to proceed:</p>
                    
                    <div class="otp-box">
                        <div class="otp-code">{otp_code}</div>
                        <p style="margin: 10px 0 0; color: #555;">This OTP is valid for <strong>10 minutes</strong> only.</p>
                    </div>
                    
                    <p class="warning">
                        ⚠️ <strong>Security Notice:</strong> Do not share this OTP with anyone. 
                        The system will never ask for this code via phone or chat. 
                        If you did not request this OTP, please ignore this email and 
                        consider changing your password immediately.
                    </p>
                </div>
                <div class="footer">
                    <p>This is an automated message from the District 1 Health EMR System.</p>
                    <p>© {2024} District 1 Health Office. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text fallback para sa mga email client na hindi sumusuporta ng HTML
        text_content = f"""
        District 1 Health EMR System - OTP Verification
        
        Dear {recipient_name},
        
        Your OTP for {action_text} is: {otp_code}
        
        This OTP is valid for 10 minutes only.
        
        DO NOT share this OTP with anyone.
        """

        # I-attach ang dalawang versions ng email
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        # Ipadala ang email gamit ang SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()  # I-enable ang TLS encryption
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipient_email, msg.as_string())

        print(f"✅ OTP email sent successfully to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send OTP email: {e}")
        return False


def send_account_created_email(recipient_email: str, recipient_name: str, temp_password: str) -> bool:
    """
    Magpadala ng notification email sa bagong BHW account.
    Kasama ang temporary password na dapat palitan agad.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "EMR System - Your Account Has Been Created"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = recipient_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #0a4f76, #1a8a5e); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; }}
                .body {{ padding: 30px; }}
                .cred-box {{ background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px; margin: 15px 0; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏥 District 1 Health EMR System</h1>
                </div>
                <div class="body">
                    <p>Dear <strong>{recipient_name}</strong>,</p>
                    <p>Your BHW account has been created by the System Administrator.</p>
                    
                    <div class="cred-box">
                        <p><strong>Email:</strong> {recipient_email}</p>
                        <p><strong>Temporary Password:</strong> {temp_password}</p>
                    </div>
                    
                    <p>⚠️ Please log in immediately and change your password.</p>
                </div>
                <div class="footer">
                    <p>District 1 Health EMR System</p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipient_email, msg.as_string())

        return True
    except Exception as e:
        print(f"❌ Failed to send account created email: {e}")
        return False
