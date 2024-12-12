# app/utils/helpers.py

import streamlit as st
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import jwt
import hashlib
import re
import json
import base64
from pathlib import Path
import tempfile
import logging
import pandas as pd
import plotly.graph_objects as go
from email_validator import validate_email, EmailNotValidError
import pytz
from urllib.parse import urlparse
import requests
from app.config.settings import settings

logger = logging.getLogger(__name__)

class SecurityHelpers:
    """Security-related utility functions"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_token(data: Dict, expiry_hours: int = 24) -> str:
        """Generate JWT token"""
        try:
            payload = {
                **data,
                'exp': datetime.utcnow() + timedelta(hours=expiry_hours)
            }
            return jwt.encode(payload, settings.JWT_SECRET.get_secret_value(), algorithm='HS256')
        except Exception as e:
            logger.error(f"Error generating token: {str(e)}")
            raise

    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            return jwt.decode(token, settings.JWT_SECRET.get_secret_value(), algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            return None

class ValidationHelpers:
    """Data validation utility functions"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email address"""
        try:
            validate_email(email)
            return True, ""
        except EmailNotValidError as e:
            return False, str(e)

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        # Remove HTML tags
        clean_text = re.compile('<.*?>').sub('', text)
        # Remove special characters
        clean_text = re.compile('[^a-zA-Z0-9\s\-_.,!?]').sub('', clean_text)
        return clean_text.strip()

class DataHelpers:
    """Data manipulation utility functions"""
    
    @staticmethod
    def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime object"""
        return dt.strftime(format)

    @staticmethod
    def parse_datetime(dt_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse datetime string"""
        try:
            return datetime.strptime(dt_str, format)
        except ValueError:
            return None

    @staticmethod
    def to_local_timezone(dt: datetime, timezone: str = "UTC") -> datetime:
        """Convert datetime to local timezone"""
        local_tz = pytz.timezone(timezone)
        return dt.astimezone(local_tz)

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

class UIHelpers:
    """UI utility functions"""
    
    @staticmethod
    def render_success_message(message: str):
        """Render success message with custom styling"""
        st.markdown(f"""
        <div style='
            padding: 1rem;
            background-color: #d4edda;
            border-color: #c3e6cb;
            border-radius: 0.25rem;
            color: #155724;
            margin-bottom: 1rem;
        '>
            âœ… {message}
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_error_message(message: str):
        """Render error message with custom styling"""
        st.markdown(f"""
        <div style='
            padding: 1rem;
            background-color: #f8d7da;
            border-color: #f5c6cb;
            border-radius: 0.25rem;
            color: #721c24;
            margin-bottom: 1rem;
        '>
            âŒ {message}
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def create_download_link(data: Any, filename: str, mime_type: str = "text/plain"):
        """Create download link for data"""
        if isinstance(data, (dict, list)):
            data = json.dumps(data, indent=2)
        b64 = base64.b64encode(data.encode()).decode()
        href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}">Download {filename}</a>'
        return href

    @staticmethod
    def render_metrics_chart(data: Dict[str, float], title: str = "Metrics"):
        """Render metrics using Plotly"""
        fig = go.Figure(data=[
            go.Bar(x=list(data.keys()), y=list(data.values()))
        ])
        fig.update_layout(title=title)
        return fig

class FileHelpers:
    """File handling utility functions"""
    
    @staticmethod
    def create_temp_file(content: bytes, suffix: str = "") -> str:
        """Create temporary file and return path"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            return temp_file.name

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension"""
        return Path(filename).suffix.lower()

    @staticmethod
    def is_allowed_file(filename: str, allowed_extensions: List[str]) -> bool:
        """Check if file extension is allowed"""
        return FileHelpers.get_file_extension(filename) in allowed_extensions

    @staticmethod
    def read_file_chunks(file_path: str, chunk_size: int = 8192):
        """Generator to read file in chunks"""
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

class APIHelpers:
    """API-related utility functions"""
    
    @staticmethod
    async def make_request(url: str, method: str = "GET", **kwargs) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None

    @staticmethod
    def format_api_response(data: Any, success: bool = True) -> Dict:
        """Format API response"""
        return {
            "success": success,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

class CacheHelpers:
    """Caching utility functions"""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def cache_data(func):
        """Cache function results"""
        return func

    @staticmethod
    @st.cache_resource
    def cache_resource(func):
        """Cache resource-intensive operations"""
        return func

class AnalyticsHelpers:
    """Analytics utility functions"""
    
    @staticmethod
    def calculate_metrics(data: pd.DataFrame) -> Dict[str, float]:
        """Calculate common metrics from DataFrame"""
        metrics = {
            "total": len(data),
            "mean": data.mean(),
            "median": data.median(),
            "std": data.std()
        }
        return metrics

    @staticmethod
    def generate_summary_stats(data: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary statistics"""
        return {
            "basic_stats": data.describe().to_dict(),
            "missing_values": data.isnull().sum().to_dict(),
            "unique_values": data.nunique().to_dict()
        }

# Usage example
if __name__ == "__main__":
    # Test security helpers
    token = SecurityHelpers.generate_token({"user_id": "123"})
    decoded = SecurityHelpers.verify_token(token)
    print(f"Token verification: {decoded}")

    # Test validation helpers
    email_valid, error = ValidationHelpers.validate_email("test@example.com")
    print(f"Email validation: {email_valid}")

    # Test data helpers
    now = datetime.now()
    formatted = DataHelpers.format_datetime(now)
    print(f"Formatted datetime: {formatted}")

    # Test file helpers
    ext = FileHelpers.get_file_extension("test.pdf")
    print(f"File extension: {ext}")