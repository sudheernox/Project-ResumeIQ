"""
Email service for ResumeIQ.
Provides SMTP-based email dispatching with graceful handling of unconfigured environments.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app


def is_smtp_configured():
    """Check if SMTP credentials are provided in configuration."""
    cfg = current_app.config
    server = cfg.get('MAIL_SERVER')
    username = cfg.get('MAIL_USERNAME')
    password = cfg.get('MAIL_PASSWORD')
    return bool(server and username and password)


def send_password_reset_email(to_email, reset_url):
    """
    Send a secure password reset link to user's email via SMTP.
    Returns:
        dict: {
            'sent': bool,
            'configured': bool,
            'error': str or None
        }
    """
    if not is_smtp_configured():
        return {
            'sent': False,
            'configured': False,
            'error': 'SMTP credentials are not configured in environment variables (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD).'
        }

    cfg = current_app.config
    server_host = cfg.get('MAIL_SERVER')
    port = cfg.get('MAIL_PORT', 587)
    use_tls = cfg.get('MAIL_USE_TLS', True)
    username = cfg.get('MAIL_USERNAME')
    password = cfg.get('MAIL_PASSWORD')
    sender = cfg.get('MAIL_DEFAULT_SENDER', 'noreply@resumeiq.ai')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'ResumeIQ — Password Reset Request'
    msg['From'] = f"ResumeIQ <{sender}>"
    msg['To'] = to_email

    text_content = f"""Hello,

We received a request to reset your password for your ResumeIQ account.
To choose a new password, open the link below in your browser:
{reset_url}

This link is valid for 1 hour and can only be used once.
If you did not make this request, you can safely ignore this email.

Best regards,
The ResumeIQ Team
"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 0; background-color: #0a0e1a; font-family: 'Segoe UI', Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 15px;">
            <tr>
                <td align="center">
                    <table width="100%" max-width="540" cellpadding="0" cellspacing="0" style="max-width: 540px; background-color: #0f172a; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 36px 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                        <tr>
                            <td align="center" style="padding-bottom: 24px;">
                                <h1 style="margin: 0; font-size: 26px; font-weight: bold; color: #ffffff;">
                                    Resume<span style="color: #22d3ee;">IQ</span>
                                </h1>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <h2 style="margin: 0 0 14px; font-size: 18px; color: #ffffff;">Password Reset Request</h2>
                                <p style="margin: 0 0 20px; font-size: 14px; line-height: 1.6; color: #94a3b8;">
                                    We received a request to reset the password for your ResumeIQ account. Click the button below to set a new password:
                                </p>
                            </td>
                        </tr>
                        <tr>
                            <td align="center" style="padding: 16px 0 28px;">
                                <a href="{reset_url}" target="_blank" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff; text-decoration: none; padding: 12px 32px; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);">
                                    Reset Password
                                </a>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <p style="margin: 0 0 10px; font-size: 13px; color: #64748b; line-height: 1.5;">
                                    • This link will expire in <strong>1 hour</strong> and can only be used once.<br>
                                    • If you did not request a password reset, you can safely ignore this message.
                                </p>
                                <hr style="border: 0; border-top: 1px solid rgba(255, 255, 255, 0.08); margin: 24px 0 18px;">
                                <p style="margin: 0; font-size: 11px; color: #475569; word-break: break-all;">
                                    If the button doesn't work, copy and paste this link into your browser:<br>
                                    <a href="{reset_url}" style="color: #38bdf8; text-decoration: underline;">{reset_url}</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_content, 'plain'))
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP(server_host, port, timeout=12)
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.sendmail(sender, [to_email], msg.as_string())
        server.quit()
        return {'sent': True, 'configured': True, 'error': None}
    except Exception as e:
        return {'sent': False, 'configured': True, 'error': f"SMTP dispatch failed: {str(e)}"}
