# app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Dict, Optional, Union, Any
import asyncio
from pathlib import Path
import jinja2
import logging
from datetime import datetime
import aiosmtplib
from app.config.settings import settings
import json
import base64
from email.utils import formataddr

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        """Initialize email service"""
        try:
            self.smtp_host = settings.SMTP_HOST
            self.smtp_port = settings.SMTP_PORT
            self.smtp_user = settings.SMTP_USER.get_secret_value()
            self.smtp_password = settings.SMTP_PASSWORD.get_secret_value()
            self.sender_email = settings.SENDER_EMAIL
            self.sender_name = settings.SENDER_NAME
            
            # Initialize Jinja2 template environment
            self.template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(
                    Path(__file__).parent.parent / 'templates' / 'email'
                )
            )
            
            # Email templates
            self.templates = {
                'welcome': 'welcome.html',
                'interview_report': 'interview_report.html',
                'subscription_confirmation': 'subscription_confirmation.html',
                'payment_failed': 'payment_failed.html',
                'subscription_canceled': 'subscription_canceled.html',
                'password_reset': 'password_reset.html',
                'interview_reminder': 'interview_reminder.html'
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize email service: {str(e)}")
            raise

    async def send_email(self,
                        to_email: Union[str, List[str]],
                        subject: str,
                        template_name: str,
                        template_data: Dict[str, Any],
                        attachments: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Send email using template
        
        Args:
            to_email: Recipient email(s)
            subject: Email subject
            template_name: Name of the template to use
            template_data: Data to populate template
            attachments: List of attachment dictionaries
            
        Returns:
            Boolean indicating success
        """
        try:
            # Prepare recipient list
            recipients = [to_email] if isinstance(to_email, str) else to_email
            
            # Create message
            msg = self._create_message(
                recipients,
                subject,
                template_name,
                template_data,
                attachments
            )
            
            # Send email asynchronously
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=True
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_password)
                await smtp.send_message(msg)
            
            logger.info(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False

    def _create_message(self,
                       recipients: List[str],
                       subject: str,
                       template_name: str,
                       template_data: Dict[str, Any],
                       attachments: Optional[List[Dict[str, Any]]] = None) -> MIMEMultipart:
        """Create email message with template"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((self.sender_name, self.sender_email))
        msg['To'] = ', '.join(recipients)
        
        # Render template
        template = self.template_env.get_template(self.templates[template_name])
        html_content = template.render(**template_data)
        
        # Add HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                self._add_attachment(msg, attachment)
        
        return msg

    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message"""
        try:
            if 'content' in attachment:
                part = MIMEApplication(attachment['content'])
            elif 'path' in attachment:
                with open(attachment['path'], 'rb') as f:
                    part = MIMEApplication(f.read())
            else:
                raise ValueError("Attachment must contain either 'content' or 'path'")
            
            part.add_header(
                'Content-Disposition',
                'attachment',
                filename=attachment['filename']
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment: {str(e)}")
            raise

    async def send_welcome_email(self, user_data: Dict[str, Any]) -> bool:
        """Send welcome email to new user"""
        template_data = {
            'user_name': user_data['name'],
            'login_url': f"{settings.APP_URL}/login",
            'help_url': f"{settings.APP_URL}/help",
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Welcome to Beaver Job Interview Trainer!",
            'welcome',
            template_data
        )

    async def send_interview_report(self,
                                  user_data: Dict[str, Any],
                                  report_data: Dict[str, Any]) -> bool:
        """Send interview report email"""
        template_data = {
            'user_name': user_data['name'],
            'interview_date': report_data['date'],
            'company_name': report_data['company_name'],
            'overall_score': report_data['scores']['overall'],
            'feedback': report_data['feedback'],
            'report_url': f"{settings.APP_URL}/report/{report_data['id']}",
            'current_year': datetime.now().year
        }
        
        # Create PDF attachment
        pdf_attachment = {
            'content': self._generate_pdf_report(report_data),
            'filename': f"Interview_Report_{report_data['id']}.pdf"
        }
        
        return await self.send_email(
            user_data['email'],
            "Your Interview Report is Ready!",
            'interview_report',
            template_data,
            [pdf_attachment]
        )

    async def send_subscription_confirmation(self,
                                          user_data: Dict[str, Any],
                                          subscription_data: Dict[str, Any]) -> bool:
        """Send subscription confirmation email"""
        template_data = {
            'user_name': user_data['name'],
            'plan_name': subscription_data['plan'],
            'amount': subscription_data['amount'],
            'next_billing_date': subscription_data['next_billing_date'],
            'manage_url': f"{settings.APP_URL}/subscription",
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Subscription Confirmation",
            'subscription_confirmation',
            template_data
        )

    async def send_payment_failed(self,
                                user_data: Dict[str, Any],
                                payment_data: Dict[str, Any]) -> bool:
        """Send payment failure notification"""
        template_data = {
            'user_name': user_data['name'],
            'amount': payment_data['amount'],
            'next_attempt': payment_data['next_attempt'],
            'update_payment_url': f"{settings.APP_URL}/subscription/payment",
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Payment Failed - Action Required",
            'payment_failed',
            template_data
        )

    async def send_subscription_canceled(self, user_data: Dict[str, Any]) -> bool:
        """Send subscription cancellation confirmation"""
        template_data = {
            'user_name': user_data['name'],
            'end_date': user_data['subscription_end_date'],
            'reactivate_url': f"{settings.APP_URL}/subscription",
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Subscription Cancellation Confirmation",
            'subscription_canceled',
            template_data
        )

    async def send_password_reset(self,
                                user_data: Dict[str, Any],
                                reset_token: str) -> bool:
        """Send password reset email"""
        template_data = {
            'user_name': user_data['name'],
            'reset_url': f"{settings.APP_URL}/reset-password?token={reset_token}",
            'expiry_hours': 24,
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Password Reset Request",
            'password_reset',
            template_data
        )

    async def send_interview_reminder(self,
                                    user_data: Dict[str, Any],
                                    interview_data: Dict[str, Any]) -> bool:
        """Send interview reminder email"""
        template_data = {
            'user_name': user_data['name'],
            'interview_time': interview_data['scheduled_time'],
            'company_name': interview_data['company_name'],
            'preparation_tips': self._get_preparation_tips(),
            'interview_url': f"{settings.APP_URL}/interview/{interview_data['id']}",
            'current_year': datetime.now().year
        }
        
        return await self.send_email(
            user_data['email'],
            "Interview Reminder",
            'interview_reminder',
            template_data
        )

    def _generate_pdf_report(self, report_data: Dict[str, Any]) -> bytes:
        """Generate PDF report"""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Create the PDF content
            content = []
            
            # Add report content
            # ... (PDF generation logic)
            
            doc.build(content)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {str(e)}")
            raise

    def _get_preparation_tips(self) -> List[str]:
        """Get interview preparation tips"""
        return [
            "Review your resume and practice discussing your experience",
            "Research the company and position",
            "Prepare questions for the interviewer",
            "Test your audio and video equipment",
            "Find a quiet location for the interview"
        ]

# Initialize email service
email_service = EmailService()

if __name__ == "__main__":
    # Test email service
    async def test_email_service():
        # Test welcome email
        user_data = {
            'name': 'Test User',
            'email': 'test@example.com'
        }
        
        success = await email_service.send_welcome_email(user_data)
        print(f"Welcome email sent: {success}")
        
        # Test interview report email
        report_data = {
            'id': '123',
            'date': datetime.now(),
            'company_name': 'Test Company',
            'scores': {'overall': 85},
            'feedback': {'strengths': ['Good communication'], 'improvements': ['Practice more']}
        }
        
        success = await email_service.send_interview_report(user_data, report_data)
        print(f"Report email sent: {success}")

    asyncio.run(test_email_service())