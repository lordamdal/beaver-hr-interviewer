# app/database/operations.py

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.database.models import User, Resume, Interview, AdminSettings, get_db
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseOperations:
    def __init__(self):
        self.db = next(get_db())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

class UserOperations(DatabaseOperations):
    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        try:
            user = User(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return User.to_dict(user)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            return User.to_dict(user)
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def update_subscription(self, user_id: str, plan: str) -> bool:
        """Update user subscription"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            plan_details = settings.SUBSCRIPTION_PLANS.get(plan)
            if not plan_details:
                return False

            user.subscription_plan = plan
            user.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            user.interviews_remaining = plan_details['interviews_per_month']
            
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating subscription: {str(e)}")
            return False

    def decrement_interviews(self, user_id: str) -> bool:
        """Decrement remaining interviews count"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.interviews_remaining <= 0:
                return False

            user.interviews_remaining -= 1
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error decrementing interviews: {str(e)}")
            return False

class ResumeOperations(DatabaseOperations):
    def save_resume(self, user_id: str, file_path: str, parsed_data: Dict) -> Optional[str]:
        """Save resume information"""
        try:
            resume = Resume(
                user_id=user_id,
                file_path=file_path,
                parsed_data=parsed_data
            )
            self.db.add(resume)
            self.db.commit()
            return str(resume.id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving resume: {str(e)}")
            return None

    def get_user_resumes(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all resumes for a user"""
        try:
            resumes = self.db.query(Resume).filter(Resume.user_id == user_id).all()
            return [
                {
                    'id': str(resume.id),
                    'file_path': resume.file_path,
                    'parsed_data': resume.parsed_data,
                    'created_at': resume.created_at
                }
                for resume in resumes
            ]
        except Exception as e:
            logger.error(f"Error getting resumes: {str(e)}")
            return []

class InterviewOperations(DatabaseOperations):
    def create_interview(self, interview_data: Dict[str, Any]) -> Optional[str]:
        """Create new interview record"""
        try:
            interview = Interview(**interview_data)
            self.db.add(interview)
            self.db.commit()
            return str(interview.id)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating interview: {str(e)}")
            return None

    def update_interview_results(self, interview_id: str, 
                               score: int, feedback: Dict,
                               recording_url: Optional[str] = None,
                               transcript: Optional[str] = None) -> bool:
        """Update interview results"""
        try:
            interview = self.db.query(Interview).filter(Interview.id == interview_id).first()
            if not interview:
                return False

            interview.total_score = score
            interview.feedback = feedback
            if recording_url:
                interview.recording_url = recording_url
            if transcript:
                interview.transcript = transcript

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating interview results: {str(e)}")
            return False

    def get_user_interviews(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all interviews for a user"""
        try:
            interviews = (
                self.db.query(Interview)
                .filter(Interview.user_id == user_id)
                .order_by(desc(Interview.created_at))
                .all()
            )
            return [
                {
                    'id': str(interview.id),
                    'company_name': interview.company_name,
                    'total_score': interview.total_score,
                    'feedback': interview.feedback,
                    'created_at': interview.created_at,
                    'recording_url': interview.recording_url if interview.recording_url else None
                }
                for interview in interviews
            ]
        except Exception as e:
            logger.error(f"Error getting interviews: {str(e)}")
            return []

class AdminOperations(DatabaseOperations):
    def save_setting(self, key: str, value: str, is_sensitive: bool = False) -> bool:
        """Save admin setting"""
        try:
            setting = self.db.query(AdminSettings).filter(
                AdminSettings.setting_key == key
            ).first()

            if setting:
                setting.setting_value = value
                setting.is_sensitive = is_sensitive
            else:
                setting = AdminSettings(
                    setting_key=key,
                    setting_value=value,
                    is_sensitive=is_sensitive
                )
                self.db.add(setting)

            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving setting: {str(e)}")
            return False

    def get_setting(self, key: str) -> Optional[str]:
        """Get admin setting value"""
        try:
            setting = self.db.query(AdminSettings).filter(
                AdminSettings.setting_key == key
            ).first()
            return setting.setting_value if setting else None
        except Exception as e:
            logger.error(f"Error getting setting: {str(e)}")
            return None

    def get_all_settings(self, include_sensitive: bool = False) -> Dict[str, str]:
        """Get all admin settings"""
        try:
            query = self.db.query(AdminSettings)
            if not include_sensitive:
                query = query.filter(AdminSettings.is_sensitive == False)
            
            settings = query.all()
            return {
                setting.setting_key: setting.setting_value
                for setting in settings
            }
        except Exception as e:
            logger.error(f"Error getting all settings: {str(e)}")
            return {}

# Usage example:
if __name__ == "__main__":
    # Test database operations
    with UserOperations() as user_ops:
        test_user = {
            "name": "Test User",
            "phone": "+1234567890",
            "email": "test@example.com"
        }
        user = user_ops.create_user(test_user)
        print(f"Created user: {user}")