# app/components/profile.py

import streamlit as st
from typing import Dict, Optional, List
import logging
from datetime import datetime
from app.database.operations import UserOperations
from app.services.storage_service import StorageService
from app.utils.helpers import ValidationHelpers, UIHelpers
from app.auth.authentication import require_auth
from app.services.email_service import email_service
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from pathlib import Path
import base64

logger = logging.getLogger(__name__)

class ProfileComponent:
    def __init__(self):
        """Initialize profile component"""
        self.user_ops = UserOperations()
        self.storage_service = StorageService()
        self.validators = ValidationHelpers()
        self.ui_helpers = UIHelpers()

    @require_auth
    def render(self):
        """Render the profile interface"""
        st.title("Profile Settings")

        # Apply custom styling
        self._apply_custom_styles()

        # Get user data
        user_data = self.user_ops.get_user(st.session_state.user_id)
        if not user_data:
            st.error("Error loading user profile")
            return

        # Create tabs for different sections
        tabs = st.tabs([
            "Profile Information",
            "Interview History",
            "Resume Management",
            "Preferences",
            "Account Settings"
        ])

        # Profile Information
        with tabs[0]:
            self._render_profile_information(user_data)

        # Interview History
        with tabs[1]:
            self._render_interview_history(user_data)

        # Resume Management
        with tabs[2]:
            self._render_resume_management(user_data)

        # Preferences
        with tabs[3]:
            self._render_preferences(user_data)

        # Account Settings
        with tabs[4]:
            self._render_account_settings(user_data)

    def _apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .profile-section {
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stat-card {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 1rem;
        }
        .profile-header {
            display: flex;
            align-items: center;
            margin-bottom: 2rem;
        }
        .avatar {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            margin-right: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)

    def _render_profile_information(self, user_data: Dict):
        """Render profile information section"""
        st.header("Profile Information")

        # Profile picture and basic info
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if user_data.get('avatar_url'):
                st.image(user_data['avatar_url'], width=150)
            else:
                st.image("default_avatar.png", width=150)
            
            uploaded_file = st.file_uploader("Update Profile Picture", type=['jpg', 'png'])
            if uploaded_file:
                self._update_profile_picture(uploaded_file)

        with col2:
            with st.form("profile_form"):
                name = st.text_input("Full Name", value=user_data.get('name', ''))
                email = st.text_input("Email", value=user_data.get('email', ''))
                phone = st.text_input("Phone", value=user_data.get('phone', ''))
                location = st.text_input("Location", value=user_data.get('location', ''))
                
                if st.form_submit_button("Update Profile"):
                    self._update_profile_info({
                        'name': name,
                        'email': email,
                        'phone': phone,
                        'location': location
                    })

        # Professional Information
        st.subheader("Professional Information")
        with st.form("professional_info_form"):
            title = st.text_input("Job Title", value=user_data.get('title', ''))
            company = st.text_input("Current Company", value=user_data.get('company', ''))
            industry = st.text_input("Industry", value=user_data.get('industry', ''))
            experience = st.number_input("Years of Experience", 
                                       value=int(user_data.get('experience', 0)))
            
            if st.form_submit_button("Update Professional Info"):
                self._update_professional_info({
                    'title': title,
                    'company': company,
                    'industry': industry,
                    'experience': experience
                })

    def _render_interview_history(self, user_data: Dict):
        """Render interview history section"""
        st.header("Interview History")

        # Interview Statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_interviews = len(user_data.get('interviews', []))
            st.metric("Total Interviews", total_interviews)
            
        with col2:
            avg_score = self._calculate_average_score(user_data.get('interviews', []))
            st.metric("Average Score", f"{avg_score:.1f}%")
            
        with col3:
            improvement_rate = self._calculate_improvement_rate(
                user_data.get('interviews', [])
            )
            st.metric("Improvement Rate", f"{improvement_rate:+.1f}%")

        # Interview Timeline
        if user_data.get('interviews'):
            self._render_interview_timeline(user_data['interviews'])

        # Recent Interviews
        st.subheader("Recent Interviews")
        for interview in user_data.get('interviews', [])[-5:]:
            with st.expander(
                f"{interview['company_name']} - {interview['date'].strftime('%Y-%m-%d')}"
            ):
                self._render_interview_details(interview)

    def _render_resume_management(self, user_data: Dict):
        """Render resume management section"""
        st.header("Resume Management")

        # Upload new resume
        uploaded_file = st.file_uploader("Upload New Resume", type=['pdf', 'docx'])
        if uploaded_file:
            self._handle_resume_upload(uploaded_file)

        # Existing Resumes
        st.subheader("Your Resumes")
        resumes = self.storage_service.list_user_files(
            st.session_state.user_id,
            file_type="resume"
        )
        
        if resumes:
            for resume in resumes:
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(resume['name'])
                    
                with col2:
                    st.write(f"Uploaded: {resume['created'].strftime('%Y-%m-%d')}")
                    
                with col3:
                    if st.button("Delete", key=f"delete_{resume['id']}"):
                        self._delete_resume(resume['id'])

    def _render_preferences(self, user_data: Dict):
        """Render user preferences section"""
        st.header("Preferences")

        # Interview Preferences
        st.subheader("Interview Preferences")
        with st.form("interview_preferences"):
            difficulty = st.select_slider(
                "Interview Difficulty",
                options=["Easy", "Medium", "Hard"],
                value=user_data.get('preferences', {}).get('difficulty', "Medium")
            )
            
            focus_areas = st.multiselect(
                "Focus Areas",
                ["Technical Skills", "Behavioral", "Leadership", "Problem Solving"],
                default=user_data.get('preferences', {}).get('focus_areas', [])
            )
            
            interview_duration = st.slider(
                "Preferred Interview Duration (minutes)",
                15, 60, 
                value=user_data.get('preferences', {}).get('duration', 30)
            )
            
            if st.form_submit_button("Save Preferences"):
                self._update_preferences({
                    'difficulty': difficulty,
                    'focus_areas': focus_areas,
                    'duration': interview_duration
                })

        # Notification Preferences
        st.subheader("Notification Preferences")
        with st.form("notification_preferences"):
            email_notifications = st.checkbox(
                "Email Notifications",
                value=user_data.get('preferences', {}).get('email_notifications', True)
            )
            
            notification_types = st.multiselect(
                "Notification Types",
                ["Interview Reminders", "Reports Ready", "Tips & Advice"],
                default=user_data.get('preferences', {}).get('notification_types', [])
            )
            
            if st.form_submit_button("Save Notification Preferences"):
                self._update_notification_preferences({
                    'email_notifications': email_notifications,
                    'notification_types': notification_types
                })

    def _render_account_settings(self, user_data: Dict):
        """Render account settings section"""
        st.header("Account Settings")

        # Change Password
        st.subheader("Change Password")
        with st.form("change_password"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Change Password"):
                self._change_password(current_password, new_password, confirm_password)

        # Delete Account
        st.subheader("Delete Account")
        st.warning("Warning: This action cannot be undone!")
        
        with st.form("delete_account"):
            confirm_delete = st.text_input(
                "Type 'DELETE' to confirm account deletion"
            )
            if st.form_submit_button("Delete Account"):
                if confirm_delete == "DELETE":
                    self._delete_account()
                else:
                    st.error("Please type 'DELETE' to confirm account deletion")

    def _update_profile_picture(self, file):
        """Update user's profile picture"""
        try:
            success, url = self.storage_service.upload_file(
                file.read(),
                file.name,
                st.session_state.user_id,
                "avatars"
            )
            
            if success:
                self.user_ops.update_user(st.session_state.user_id, {
                    'avatar_url': url
                })
                st.success("Profile picture updated successfully!")
                st.experimental_rerun()
            else:
                st.error("Failed to update profile picture")
                
        except Exception as e:
            logger.error(f"Error updating profile picture: {str(e)}")
            st.error("An error occurred while updating profile picture")

    def _update_profile_info(self, data: Dict):
        """Update user's profile information"""
        try:
            # Validate data
            if not self.validators.validate_email(data['email'])[0]:
                st.error("Invalid email address")
                return
                
            if not self.validators.validate_phone(data['phone']):
                st.error("Invalid phone number")
                return

            # Update user data
            self.user_ops.update_user(st.session_state.user_id, data)
            st.success("Profile updated successfully!")
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            st.error("An error occurred while updating profile")

    def _calculate_average_score(self, interviews: List[Dict]) -> float:
        """Calculate average interview score"""
        if not interviews:
            return 0.0
        return sum(interview['score'] for interview in interviews) / len(interviews)

    def _calculate_improvement_rate(self, interviews: List[Dict]) -> float:
        """Calculate improvement rate between first and last interviews"""
        if len(interviews) < 2:
            return 0.0
        first_score = interviews[0]['score']
        last_score = interviews[-1]['score']
        return ((last_score - first_score) / first_score) * 100

    def _render_interview_timeline(self, interviews: List[Dict]):
        """Render interview score timeline"""
        df = pd.DataFrame([
            {
                'date': interview['date'],
                'score': interview['score'],
                'company': interview['company_name']
            }
            for interview in interviews
        ])
        
        fig = px.line(df, x='date', y='score', 
                     hover_data=['company'],
                     title='Interview Performance Over Time')
        st.plotly_chart(fig)

    def _handle_resume_upload(self, file):
        """Handle resume upload"""
        try:
            success, url = self.storage_service.upload_file(
                file.read(),
                file.name,
                st.session_state.user_id,
                "resumes"
            )
            
            if success:
                st.success("Resume uploaded successfully!")
                st.experimental_rerun()
            else:
                st.error("Failed to upload resume")
                
        except Exception as e:
            logger.error(f"Error uploading resume: {str(e)}")
            st.error("An error occurred while uploading resume")

# Initialize component
profile_component = ProfileComponent()

if __name__ == "__main__":
    profile_component.render()