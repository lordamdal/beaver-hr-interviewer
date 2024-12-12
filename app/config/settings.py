# app/config/settings.py

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import SecretStr, Field

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Project base directory
    BASE_DIR: Path = Path(__file__).parent.parent.parent

    # Application settings
    APP_NAME: str = "Beaver Job Interview Trainer"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    APP_URL: str = Field(default="http://localhost:8501")
    
    # Google Cloud Settings
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Cloud SQL Settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "beaver_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: SecretStr = SecretStr(os.getenv("DB_PASSWORD", ""))
    
    # Cloud Storage Settings
    BUCKET_NAME: str = os.getenv("BUCKET_NAME", "beaver-storage")
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID: SecretStr = SecretStr(os.getenv("TWILIO_ACCOUNT_SID", ""))
    TWILIO_AUTH_TOKEN: SecretStr = SecretStr(os.getenv("TWILIO_AUTH_TOKEN", ""))
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Stripe Settings
    STRIPE_SECRET_KEY: SecretStr = Field(default=SecretStr(""))
    STRIPE_PUBLISHABLE_KEY: str = Field(default="")
    STRIPE_WEBHOOK_SECRET: SecretStr = Field(default=SecretStr(""))

    # Email Settings
    SMTP_HOST: str = Field(default="smtp.gmail.com")
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str = Field(default="")
    SMTP_PASSWORD: SecretStr = Field(default=SecretStr(""))
    SENDER_EMAIL: str = Field(default="noreply@beaverinterviews.com")
    SENDER_NAME: str = Field(default="Beaver Interviews")

    # Firebase Settings
    FIREBASE_CREDENTIALS_PATH: str = Field(default="")
    
    # JWT Settings
    JWT_SECRET: SecretStr = SecretStr(os.getenv("JWT_SECRET", "your-secret-key"))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Admin Settings
    ADMIN_PASSWORD: SecretStr = SecretStr(os.getenv("ADMIN_PASSWORD", "admin123"))
    
    # Subscription Plans
    SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
        "free": {
            "name": "Free Trial",
            "price": 0,
            "interviews_per_month": 1,
            "features": ["Basic Interview", "Basic Report"]
        },
        "basic": {
            "name": "Basic Plan",
            "price": 9.99,
            "interviews_per_month": 5,
            "features": ["Basic Interview", "Detailed Report", "Email Report"]
        },
        "premium": {
            "name": "Premium Plan",
            "price": 29.99,
            "interviews_per_month": 20,
            "features": ["Advanced Interview", "Detailed Report", "Email Report", 
                        "Call Recording", "Priority Support"]
        }
    }

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the settings

def get_db_url() -> str:
    """Generate database URL from settings"""
    return f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD.get_secret_value()}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Create settings instance
settings = Settings()

# Example .env file template
ENV_TEMPLATE = """
DEBUG=False
APP_NAME="Beaver Job Interview Trainer"
APP_URL="http://localhost:8501"

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=beaver_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_phone_number

# Stripe
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_email_password
SENDER_EMAIL=noreply@beaverinterviews.com
SENDER_NAME="Beaver Interviews"

# Firebase
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json

# Storage
BUCKET_NAME=your-storage-bucket

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Admin
ADMIN_PASSWORD=admin123
"""

def create_env_template():
    """Create a template .env file if it doesn't exist"""
    env_path = settings.BASE_DIR / ".env"
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write(ENV_TEMPLATE.strip())
        print(f"Created .env template at {env_path}")

if __name__ == "__main__":
    # Create .env template if running this file directly
    create_env_template()