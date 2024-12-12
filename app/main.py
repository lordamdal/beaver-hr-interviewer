# app/main.py

import streamlit as st
from pathlib import Path
import sys
import logging
from datetime import datetime
import json

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent
sys.path.append(str(app_dir))

# Import components
from app.components.landing_page import landing_page
from app.components.interview import interview_component
from app.components.report import report_component
from app.components.profile import profile_component
from app.components.analytics import analytics_component
from app.components.help import help_component
from app.components.support import support_component
from app.components.feedback import feedback_component
from app.admin.dashboard import admin_dashboard
from app.auth.authentication import require_auth
from app.services.notification_service import notification_service
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BeaverInterviewApp:
    def __init__(self):
        """Initialize the application"""
        self.pages = {
            "Home": self.render_home,
            "Interview": self.render_interview,
            "Reports": self.render_reports,
            "Analytics": self.render_analytics,
            "Profile": self.render_profile,
            "Help": self.render_help,
            "Support": self.render_support
        }
        
        # Initialize session state
        self.init_session_state()

    def init_session_state(self):
        """Initialize session state variables"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 'Home'
        if 'notifications' not in st.session_state:
            st.session_state.notifications = []

    def run(self):
        """Run the application"""
        try:
            # Configure Streamlit page
            st.set_page_config(
                page_title=settings.APP_NAME,
                page_icon="ðŸ¦«",
                layout="wide",
                initial_sidebar_state="expanded"
            )

            # Apply custom styling
            self.apply_custom_styles()

            # Check if admin panel is requested
            if self.is_admin_route():
                admin_dashboard.render()
                return

            # Render navigation
            self.render_navigation()

            # Render notifications
            self.render_notifications()

            # Render current page
            current_page = st.session_state.current_page
            if current_page in self.pages:
                self.pages[current_page]()

        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            self.render_error_page(str(e))

    def apply_custom_styles(self):
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        .main-header {
            padding: 1rem 0;
            background-color: #f8f9fa;
            margin-bottom: 2rem;
        }
        .notification {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
        }
        .notification.info {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        .notification.success {
            background-color: #e8f5e9;
            border-left: 4px solid #4caf50;
        }
        .notification.warning {
            background-color: #fff3e0;
            border-left: 4px solid #ff9800;
        }
        .notification.error {
            background-color: #ffebee;
            border-left: 4px solid #f44336;
        }
        </style>
        """, unsafe_allow_html=True)

    def render_navigation(self):
        """Render navigation sidebar"""
        with st.sidebar:
            st.image("assets/logo.png", width=100)
            st.title(settings.APP_NAME)
            
            if st.session_state.authenticated:
                # User info
                st.markdown(f"Welcome, {st.session_state.user_data['name']}")
                
                # Navigation
                for page in self.pages.keys():
                    if st.button(page):
                        st.session_state.current_page = page
                        st.experimental_rerun()
                
                # Logout button
                if st.button("Logout"):
                    self.handle_logout()
            else:
                st.info("Please log in to continue")

    def render_notifications(self):
        """Render notification messages"""
        if st.session_state.notifications:
            for notif in st.session_state.notifications:
                st.markdown(f"""
                <div class="notification {notif['type']}">
                    {notif['message']}
                </div>
                """, unsafe_allow_html=True)
            # Clear notifications after displaying
            st.session_state.notifications = []

    @require_auth
    def render_home(self):
        """Render home page"""
        if not st.session_state.authenticated:
            landing_page.render()
        else:
            st.title("Dashboard")
            
            # Quick actions
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Start Interview"):
                    st.session_state.current_page = "Interview"
                    st.experimental_rerun()
            with col2:
                if st.button("View Reports"):
                    st.session_state.current_page = "Reports"
                    st.experimental_rerun()
            with col3:
                if st.button("Get Help"):
                    st.session_state.current_page = "Help"
                    st.experimental_rerun()
            
            # Recent activity
            st.subheader("Recent Activity")
            recent_interviews = interview_component.get_recent_interviews(
                st.session_state.user_id
            )
            if recent_interviews:
                for interview in recent_interviews:
                    st.markdown(f"""
                    * Interview on {interview['date']} - Score: {interview['score']}%
                    """)
            else:
                st.info("No recent interviews. Start practicing!")

    @require_auth
    def render_interview(self):
        """Render interview page"""
        interview_component.render()

    @require_auth
    def render_reports(self):
        """Render reports page"""
        report_component.render()

    @require_auth
    def render_analytics(self):
        """Render analytics page"""
        analytics_component.render()

    @require_auth
    def render_profile(self):
        """Render profile page"""
        profile_component.render()

    @require_auth
    def render_help(self):
        """Render help page"""
        help_component.render()

    @require_auth
    def render_support(self):
        """Render support page"""
        support_component.render()

    def handle_logout(self):
        """Handle user logout"""
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.current_page = "Home"
        st.experimental_rerun()

    def is_admin_route(self) -> bool:
        """Check if current route is admin panel"""
        query_params = st.experimental_get_query_params()
        return query_params.get('page', [''])[0] == 'godfather'

    def render_error_page(self, error_message: str):
        """Render error page"""
        st.error("An error occurred!")
        st.write(error_message)
        if st.button("Return to Home"):
            st.session_state.current_page = "Home"
            st.experimental_rerun()

    def add_notification(self, message: str, type: str = "info"):
        """Add notification to display"""
        st.session_state.notifications.append({
            "message": message,
            "type": type,
            "timestamp": datetime.now()
        })

# Initialize and run application
app = BeaverInterviewApp()

if __name__ == "__main__":
    app.run()