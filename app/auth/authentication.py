# app/auth/authentication.py

import streamlit as st
from typing import Optional, Dict, Tuple
import re
import jwt
from datetime import datetime, timedelta
import hashlib
from app.config.settings import settings
from app.database.models import User  # We'll create this later

class Authentication:
    def __init__(self):
        self.jwt_secret = hashlib.sha256(
            settings.DB_PASSWORD.get_secret_value().encode()
        ).hexdigest()

    def _validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return bool(re.match(pattern, phone))

    def _validate_name(self, name: str) -> bool:
        """Validate name format"""
        return bool(name and len(name.strip()) >= 2)

    def _create_jwt_token(self, user_data: Dict) -> str:
        """Create JWT token for user session"""
        payload = {
            'user_id': user_data.get('id'),
            'phone': user_data.get('phone'),
            'exp': datetime.utcnow() + timedelta(days=1)
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')

    def _verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return user data"""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def login_form(self) -> Tuple[bool, Optional[str]]:
        """Display login form and handle authentication"""
        st.markdown("""
        <style>
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
            st.subheader("Login / Sign Up")

            name = st.text_input("Full Name", key="login_name")
            phone = st.text_input("Phone Number (with country code)", 
                                key="login_phone",
                                help="Example: +1234567890")

            col1, col2 = st.columns(2)
            with col1:
                login_button = st.button("Login")
            with col2:
                signup_button = st.button("Sign Up")

            st.markdown("</div>", unsafe_allow_html=True)

            if login_button or signup_button:
                if not self._validate_name(name):
                    st.error("Please enter a valid name (minimum 2 characters)")
                    return False, None

                if not self._validate_phone_number(phone):
                    st.error("Please enter a valid phone number with country code")
                    return False, None

                try:
                    if signup_button:
                        # Check if user exists
                        existing_user = User.get_by_phone(phone)
                        if existing_user:
                            st.error("Phone number already registered. Please login.")
                            return False, None
                        
                        # Create new user
                        user_data = {
                            'name': name.strip(),
                            'phone': phone,
                            'created_at': datetime.utcnow()
                        }
                        user = User.create(user_data)
                        token = self._create_jwt_token(user_data)
                        st.success("Account created successfully!")
                        
                    else:  # login_button
                        user = User.get_by_phone(phone)
                        if not user:
                            st.error("User not found. Please sign up.")
                            return False, None
                        
                        if user['name'].lower() != name.lower().strip():
                            st.error("Invalid credentials.")
                            return False, None
                        
                        token = self._create_jwt_token(user)
                        st.success("Logged in successfully!")

                    return True, token

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    return False, None

            return False, None

    def check_authentication(self) -> bool:
        """Check if user is authenticated"""
        if 'auth_token' not in st.session_state:
            return False

        user_data = self._verify_jwt_token(st.session_state.auth_token)
        if not user_data:
            # Clear invalid token
            st.session_state.pop('auth_token', None)
            return False

        return True

    def logout(self):
        """Log out user"""
        if 'auth_token' in st.session_state:
            del st.session_state.auth_token
        if 'authenticated' in st.session_state:
            st.session_state.authenticated = False

    def get_current_user(self) -> Optional[Dict]:
        """Get current user data"""
        if 'auth_token' not in st.session_state:
            return None

        return self._verify_jwt_token(st.session_state.auth_token)

# Initialize authentication
auth = Authentication()

# Helper functions for other components
def require_auth(func):
    """Decorator to require authentication for a page/function"""
    def wrapper(*args, **kwargs):
        if not auth.check_authentication():
            st.warning("Please log in to access this feature.")
            authenticated, token = auth.login_form()
            if authenticated:
                st.session_state.auth_token = token
                st.session_state.authenticated = True
                st.experimental_rerun()
            return
        return func(*args, **kwargs)
    return wrapper

def init_auth():
    """Initialize authentication in main app"""
    if not auth.check_authentication():
        authenticated, token = auth.login_form()
        if authenticated:
            st.session_state.auth_token = token
            st.session_state.authenticated = True
            st.experimental_rerun()