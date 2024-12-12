# app/services/notification_service.py

from typing import Dict, List, Optional, Union, Any
import logging
from datetime import datetime
import asyncio
import json
from app.services.email_service import email_service
from app.services.twilio_service import TwilioService
from app.database.operations import UserOperations, NotificationOperations
from app.config.settings import settings
import streamlit as st
from enum import Enum
import queue
import threading
from dataclasses import dataclass
import firebase_admin
from firebase_admin import messaging
from firebase_admin import credentials

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Notification types enumeration"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INTERVIEW = "interview"
    PAYMENT = "payment"
    SYSTEM = "system"

@dataclass
class Notification:
    """Notification data class"""
    user_id: str
    type: NotificationType
    title: str
    message: str
    data: Optional[Dict] = None
    channels: List[str] = None
    priority: int = 0
    scheduled_for: Optional[datetime] = None

class NotificationService:
    def __init__(self):
        """Initialize notification service"""
        try:
            self.user_ops = UserOperations()
            self.notification_ops = NotificationOperations()
            self.twilio_service = TwilioService()
            
            # Initialize Firebase for push notifications
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            
            # Notification queue
            self.notification_queue = queue.PriorityQueue()
            
            # Start notification worker
            self.worker_thread = threading.Thread(
                target=self._notification_worker,
                daemon=True
            )
            self.worker_thread.start()
            
            # Notification templates
            self._load_notification_templates()
            
        except Exception as e:
            logger.error(f"Failed to initialize notification service: {str(e)}")
            raise

    def _load_notification_templates(self):
        """Load notification templates"""
        self.templates = {
            "interview_reminder": {
                "title": "Interview Reminder",
                "message": "Your interview is scheduled for {time}",
                "channels": ["email", "push", "sms"]
            },
            "interview_complete": {
                "title": "Interview Complete",
                "message": "Your interview report is ready to view",
                "channels": ["email", "push"]
            },
            "payment_success": {
                "title": "Payment Successful",
                "message": "Your payment of ${amount} was successful",
                "channels": ["email"]
            },
            "payment_failed": {
                "title": "Payment Failed",
                "message": "Your payment of ${amount} failed",
                "channels": ["email", "push", "sms"]
            },
            "subscription_expiring": {
                "title": "Subscription Expiring",
                "message": "Your subscription will expire in {days} days",
                "channels": ["email", "push"]
            }
        }

    async def send_notification(self, notification: Notification) -> bool:
        """
        Send notification through specified channels
        
        Args:
            notification: Notification object
            
        Returns:
            Boolean indicating success
        """
        try:
            # Add to queue with priority
            self.notification_queue.put(
                (notification.priority, notification)
            )
            return True
            
        except Exception as e:
            logger.error(f"Error queuing notification: {str(e)}")
            return False

    async def send_bulk_notifications(self, 
                                    notifications: List[Notification]) -> Dict[str, bool]:
        """Send multiple notifications"""
        results = {}
        for notification in notifications:
            results[notification.user_id] = await self.send_notification(notification)
        return results

    def _notification_worker(self):
        """Background worker to process notification queue"""
        while True:
            try:
                # Get notification from queue
                _, notification = self.notification_queue.get()
                
                # Process notification
                asyncio.run(self._process_notification(notification))
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in notification worker: {str(e)}")
                continue

    async def _process_notification(self, notification: Notification):
        """Process single notification"""
        try:
            user_data = self.user_ops.get_user(notification.user_id)
            if not user_data:
                logger.error(f"User not found: {notification.user_id}")
                return

            channels = notification.channels or self._get_user_preferred_channels(user_data)
            
            for channel in channels:
                if channel == "email":
                    await self._send_email_notification(notification, user_data)
                elif channel == "sms":
                    await self._send_sms_notification(notification, user_data)
                elif channel == "push":
                    await self._send_push_notification(notification, user_data)
                elif channel == "in_app":
                    await self._send_in_app_notification(notification, user_data)

            # Store notification in database
            self.notification_ops.create_notification({
                'user_id': notification.user_id,
                'type': notification.type.value,
                'title': notification.title,
                'message': notification.message,
                'data': notification.data,
                'channels': channels,
                'created_at': datetime.utcnow()
            })
            
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)}")

    async def _send_email_notification(self, 
                                     notification: Notification, 
                                     user_data: Dict):
        """Send email notification"""
        try:
            template_name = f"{notification.type.value}_notification"
            await email_service.send_email(
                user_data['email'],
                notification.title,
                template_name,
                {
                    'user_name': user_data['name'],
                    'message': notification.message,
                    'data': notification.data
                }
            )
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")

    async def _send_sms_notification(self, 
                                   notification: Notification, 
                                   user_data: Dict):
        """Send SMS notification"""
        try:
            if user_data.get('phone'):
                await self.twilio_service.send_sms(
                    user_data['phone'],
                    notification.message
                )
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")

    async def _send_push_notification(self, 
                                    notification: Notification, 
                                    user_data: Dict):
        """Send push notification"""
        try:
            if user_data.get('fcm_token'):
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notification.title,
                        body=notification.message
                    ),
                    data=notification.data or {},
                    token=user_data['fcm_token']
                )
                messaging.send(message)
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")

    async def _send_in_app_notification(self, 
                                      notification: Notification, 
                                      user_data: Dict):
        """Send in-app notification"""
        try:
            if 'notifications' not in st.session_state:
                st.session_state.notifications = []
            
            st.session_state.notifications.append({
                'type': notification.type.value,
                'title': notification.title,
                'message': notification.message,
                'timestamp': datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error sending in-app notification: {str(e)}")

    def _get_user_preferred_channels(self, user_data: Dict) -> List[str]:
        """Get user's preferred notification channels"""
        preferences = user_data.get('notification_preferences', {})
        channels = []
        
        if preferences.get('email_enabled', True):
            channels.append('email')
        if preferences.get('sms_enabled', False):
            channels.append('sms')
        if preferences.get('push_enabled', False):
            channels.append('push')
        if preferences.get('in_app_enabled', True):
            channels.append('in_app')
            
        return channels

    async def schedule_notification(self, 
                                  notification: Notification, 
                                  schedule_time: datetime) -> bool:
        """Schedule notification for future delivery"""
        try:
            notification.scheduled_for = schedule_time
            self.notification_ops.create_scheduled_notification({
                'notification': notification,
                'schedule_time': schedule_time
            })
            return True
        except Exception as e:
            logger.error(f"Error scheduling notification: {str(e)}")
            return False

    async def cancel_scheduled_notification(self, notification_id: str) -> bool:
        """Cancel scheduled notification"""
        try:
            return self.notification_ops.delete_scheduled_notification(notification_id)
        except Exception as e:
            logger.error(f"Error cancelling notification: {str(e)}")
            return False

    def get_user_notifications(self, 
                             user_id: str, 
                             limit: int = 50) -> List[Dict]:
        """Get user's notifications"""
        try:
            return self.notification_ops.get_user_notifications(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting user notifications: {str(e)}")
            return []

    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        try:
            return self.notification_ops.update_notification(
                notification_id,
                {'read': True}
            )
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

# Initialize notification service
notification_service = NotificationService()

if __name__ == "__main__":
    # Test notification service
    async def test_notifications():
        # Test basic notification
        notification = Notification(
            user_id="test_user",
            type=NotificationType.INFO,
            title="Test Notification",
            message="This is a test notification",
            channels=["email", "in_app"]
        )
        
        success = await notification_service.send_notification(notification)
        print(f"Notification sent: {success}")
        
        # Test scheduled notification
        scheduled_time = datetime.utcnow() + timedelta(hours=1)
        success = await notification_service.schedule_notification(
            notification,
            scheduled_time
        )
        print(f"Notification scheduled: {success}")

    asyncio.run(test_notifications())