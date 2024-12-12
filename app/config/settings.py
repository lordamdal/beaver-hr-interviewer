# app/config/settings.py

import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import SecretStr

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Project base directory
    BASE_DIR: Path = Path(__file__).parent.parent.parent

    # Application settings
    APP_NAME: str = "Beaver Job Interview Trainer"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
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
    
    # Mistral AI Settings
    MISTRAL_API_KEY: SecretStr = SecretStr(os.getenv("MISTRAL_API_KEY", ""))
    
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
            "features": ["Advanced Interview", "Detailed Report", "Email Report", "Call Recording", "Priority Support"]
        }
    }

    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

def get_db_url() -> str:
    """Generate database URL from settings"""
    return f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD.get_secret_value()}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Example .env file template
ENV_TEMPLATE = """
DEBUG=False
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
DB_HOST=your-db-host
DB_PORT=5432
DB_NAME=beaver_db
DB_USER=your-db-user
DB_PASSWORD=your-db-password
BUCKET_NAME=your-bucket-name
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-phone
MISTRAL_API_KEY=your-mistral-api-key
"""

def create_env_template():
    """Create a template .env file if it doesn't exist"""
    env_path = settings.BASE_DIR / ".env"
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write(ENV_TEMPLATE.strip())
        print(f"Created .env template at {env_path}")

def validate_settings() -> bool:
    """Validate that all required settings are properly configured"""
    required_settings = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "DB_HOST",
        "DB_PASSWORD",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "MISTRAL_API_KEY"
    ]
    
    missing_settings = []
    for setting in required_settings:
        value = getattr(settings, setting)
        if isinstance(value, SecretStr):
            if not value.get_secret_value():
                missing_settings.append(setting)
        elif not value:
            missing_settings.append(setting)
    
    if missing_settings:
        print(f"Missing required settings: {', '.join(missing_settings)}")
        return False
    return True

if __name__ == "__main__":
    # Create .env template if running this file directly
    create_env_template()