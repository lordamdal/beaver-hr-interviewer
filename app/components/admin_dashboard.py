# app/components/admin_dashboard.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta
from app.database.operations import AdminOperations, UserOperations, InterviewOperations
from app.config.settings import settings
from app.services.storage_service import StorageService
from app.services.llm_service import LLMService
from app.services.twilio_service import TwilioService
import logging
import json
import base64

logger = logging.getLogger(__name__)

class AdminDashboard:
    def __init__(self):
        """Initialize admin dashboard"""
        self.admin_ops = AdminOperations()
        self.user_ops = UserOperations()
        self.interview_ops = InterviewOperations()
        self.storage_service = StorageService()
        self.llm_service = LLMService()
        self.twilio_service = TwilioService()

        # Admin sections
        self.sections = {
            "overview": self._render_overview,
            "users": self._render_users_management,
            "interviews": self._render_interviews_management,
            "settings": self._render_settings,
            "api_keys": self._render_api_keys,
            "subscriptions": self._render_subscription_plans,
            "storage": self._render_storage_management,
            "logs": self._render_system_logs
        }

    def render(self):
        """Render the admin dashboard"""
        # Check admin authentication
        if not self._verify_admin():
            self._render_admin_login()
            return

        # Admin interface
        st.title("Admin Dashboard")
        
        # Sidebar navigation
        selected_section = st.sidebar.selectbox(
            "Navigation",
            list(self.sections.keys()),
            format_func=lambda x: x.title()
        )

        # Render selected section
        self.sections[selected_section]()

    def _verify_admin(self) -> bool:
        """Verify admin credentials"""
        if 'admin_authenticated' not in st.session_state:
            st.session_state.admin_authenticated = False
        return st.session_state.admin_authenticated

    def _render_admin_login(self):
        """Render admin login form"""
        st.title("Admin Login")

        with st.form("admin_login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                # Verify credentials (implement proper authentication)
                if username == "admin" and password == settings.ADMIN_PASSWORD.get_secret_value():
                    st.session_state.admin_authenticated = True
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")

    def _render_overview(self):
        """Render overview dashboard"""
        st.header("System Overview")

        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_users = self.user_ops.get_total_users()
            st.metric("Total Users", total_users)
            
        with col2:
            active_users = self.user_ops.get_active_users_count()
            st.metric("Active Users", active_users)
            
        with col3:
            total_interviews = self.interview_ops.get_total_interviews()
            st.metric("Total Interviews", total_interviews)
            
        with col4:
            premium_users = self.user_ops.get_premium_users_count()
            st.metric("Premium Users", premium_users)

        # Usage trends
        st.subheader("Usage Trends")
        usage_data = self._get_usage_data()
        fig = px.line(usage_data, x="date", y=["interviews", "new_users", "active_users"])
        st.plotly_chart(fig, use_container_width=True)

        # System health
        st.subheader("System Health")
        self._render_system_health()

    def _render_users_management(self):
        """Render user management interface"""
        st.header("User Management")

        # User search
        search_query = st.text_input("Search Users")
        
        # User filters
        col1, col2 = st.columns(2)
        with col1:
            subscription_filter = st.selectbox(
                "Subscription",
                ["All", "Free", "Basic", "Premium"]
            )
        with col2:
            status_filter = st.selectbox(
                "Status",
                ["All", "Active", "Inactive"]
            )

        # User list
        users = self.user_ops.get_filtered_users(
            search_query,
            subscription_filter,
            status_filter
        )

        if users:
            for user in users:
                with st.expander(f"{user['name']} ({user['email']})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"Subscription: {user['subscription_plan']}")
                        st.write(f"Interviews: {user['interviews_count']}")
                    
                    with col2:
                        st.write(f"Joined: {user['created_at']}")
                        st.write(f"Last Active: {user['last_active']}")
                    
                    with col3:
                        if st.button("Edit", key=f"edit_{user['id']}"):
                            self._edit_user(user)
                        if st.button("Delete", key=f"delete_{user['id']}"):
                            self._delete_user(user['id'])

    def _render_interviews_management(self):
        """Render interview management interface"""
        st.header("Interview Management")

        # Interview statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Today's Interviews", 
                     self.interview_ops.get_interviews_count(period="today"))
        with col2:
            st.metric("This Week", 
                     self.interview_ops.get_interviews_count(period="week"))
        with col3:
            st.metric("This Month", 
                     self.interview_ops.get_interviews_count(period="month"))

        # Interview list
        interviews = self.interview_ops.get_recent_interviews()
        
        if interviews:
            for interview in interviews:
                with st.expander(
                    f"Interview {interview['id']} - {interview['created_at']}"
                ):
                    self._render_interview_details(interview)

    def _render_settings(self):
        """Render system settings interface"""
        st.header("System Settings")

        # General settings
        st.subheader("General Settings")
        with st.form("general_settings"):
            app_name = st.text_input(
                "Application Name",
                value=settings.APP_NAME
            )
            debug_mode = st.checkbox(
                "Debug Mode",
                value=settings.DEBUG
            )
            max_interviews = st.number_input(
                "Max Interviews per User (Free Plan)",
                value=1
            )
            submit = st.form_submit_button("Save Settings")
            
            if submit:
                self._save_general_settings({
                    "APP_NAME": app_name,
                    "DEBUG": debug_mode,
                    "MAX_FREE_INTERVIEWS": max_interviews
                })

        # Email settings
        st.subheader("Email Settings")
        with st.form("email_settings"):
            smtp_host = st.text_input("SMTP Host")
            smtp_port = st.number_input("SMTP Port", value=587)
            smtp_user = st.text_input("SMTP Username")
            smtp_pass = st.text_input("SMTP Password", type="password")
            submit = st.form_submit_button("Save Email Settings")
            
            if submit:
                self._save_email_settings({
                    "SMTP_HOST": smtp_host,
                    "SMTP_PORT": smtp_port,
                    "SMTP_USER": smtp_user,
                    "SMTP_PASS": smtp_pass
                })

    def _render_api_keys(self):
        """Render API keys management interface"""
        st.header("API Keys Management")

        # Google Cloud settings
        st.subheader("Google Cloud")
        with st.form("google_cloud_settings"):
            project_id = st.text_input(
                "Project ID",
                value=settings.GOOGLE_CLOUD_PROJECT
            )
            credentials = st.file_uploader(
                "Service Account Credentials (JSON)",
                type=['json']
            )
            submit = st.form_submit_button("Save Google Cloud Settings")
            
            if submit:
                self._save_google_cloud_settings(project_id, credentials)

        # Twilio settings
        st.subheader("Twilio")
        with st.form("twilio_settings"):
            account_sid = st.text_input(
                "Account SID",
                value=settings.TWILIO_ACCOUNT_SID.get_secret_value()
                if settings.TWILIO_ACCOUNT_SID else ""
            )
            auth_token = st.text_input(
                "Auth Token",
                type="password",
                value=settings.TWILIO_AUTH_TOKEN.get_secret_value()
                if settings.TWILIO_AUTH_TOKEN else ""
            )
            phone_number = st.text_input(
                "Phone Number",
                value=settings.TWILIO_PHONE_NUMBER
            )
            submit = st.form_submit_button("Save Twilio Settings")
            
            if submit:
                self._save_twilio_settings({
                    "TWILIO_ACCOUNT_SID": account_sid,
                    "TWILIO_AUTH_TOKEN": auth_token,
                    "TWILIO_PHONE_NUMBER": phone_number
                })

        # Mistral AI settings
        st.subheader("Mistral AI")
        with st.form("mistral_settings"):
            api_key = st.text_input(
                "API Key",
                type="password",
                value=settings.MISTRAL_API_KEY.get_secret_value()
                if settings.MISTRAL_API_KEY else ""
            )
            submit = st.form_submit_button("Save Mistral AI Settings")
            
            if submit:
                self._save_mistral_settings(api_key)

    def _render_subscription_plans(self):
        """Render subscription plans management"""
        st.header("Subscription Plans")

        for plan_name, plan_details in settings.SUBSCRIPTION_PLANS.items():
            with st.expander(f"{plan_name.title()} Plan"):
                with st.form(f"plan_{plan_name}"):
                    price = st.number_input(
                        "Price",
                        value=float(plan_details['price'])
                    )
                    interviews = st.number_input(
                        "Interviews per Month",
                        value=int(plan_details['interviews_per_month'])
                    )
                    features = st.multiselect(
                        "Features",
                        ["Basic Interview", "Detailed Report", "Email Report",
                         "Call Recording", "Priority Support"],
                        default=plan_details['features']
                    )
                    submit = st.form_submit_button("Update Plan")
                    
                    if submit:
                        self._update_subscription_plan(
                            plan_name,
                            price,
                            interviews,
                            features
                        )

    def _render_storage_management(self):
        """Render storage management interface"""
        st.header("Storage Management")

        # Storage statistics
        storage_stats = self.storage_service.get_storage_usage(None)  # None for all users
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Storage Used", 
                     f"{storage_stats['total_size_mb']:.2f} MB")
        with col2:
            st.metric("Total Files", storage_stats['file_count'])
        with col3:
            st.metric("Active Buckets", len(storage_stats['file_types']))

        # Storage by type
        st.subheader("Storage by Type")
        fig = px.pie(
            values=list(storage_stats['file_types'].values()),
            names=list(storage_stats['file_types'].keys())
        )
        st.plotly_chart(fig, use_container_width=True)

        # Cleanup options
        st.subheader("Storage Cleanup")
        days = st.slider("Delete files older than (days)", 1, 365, 30)
        if st.button("Clean Up Old Files"):
            self.storage_service.cleanup_old_files(days)
            st.success("Cleanup completed!")

    def _render_system_logs(self):
        """Render system logs interface"""
        st.header("System Logs")

        # Log filters
        col1, col2 = st.columns(2)
        with col1:
            log_level = st.selectbox(
                "Log Level",
                ["ALL", "ERROR", "WARNING", "INFO", "DEBUG"]
            )
        with col2:
            date_range = st.date_input(
                "Date Range",
                [datetime.now() - timedelta(days=7), datetime.now()]
            )

        # Display logs
        logs = self._get_filtered_logs(log_level, date_range)
        if logs:
            for log in logs:
                with st.expander(f"{log['timestamp']} - {log['level']}"):
                    st.code(log['message'])

    def _get_usage_data(self) -> pd.DataFrame:
        """Get usage data for trends"""
        # Implement actual data gathering
        dates = pd.date_range(
            start=datetime.now() - timedelta(days=30),
            end=datetime.now()
        )
        return pd.DataFrame({
            "date": dates,
            "interviews": np.random.randint(10, 100, size=len(dates)),
            "new_users": np.random.randint(5, 50, size=len(dates)),
            "active_users": np.random.randint(50, 200, size=len(dates))
        })

    def _render_system_health(self):
        """Render system health metrics"""
        # Add actual health check implementation
        services = {
            "Database": True,
            "Storage": True,
            "LLM Service": True,
            "Twilio": True
        }
        
        for service, status in services.items():
            st.markdown(
                f"{'checking…' if status else 'at'} {service}: "
                f"{'Operational' if status else 'Down'}"
            )

# Initialize dashboard
admin_dashboard = AdminDashboard()

if __name__ == "__main__":
    admin_dashboard.render()