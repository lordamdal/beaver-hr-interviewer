# setup.py

import os
import sys
import subprocess
import logging
from pathlib import Path
import json
import psycopg2
from dotenv import load_dotenv
import streamlit as st
import google.cloud.storage
from twilio.rest import Client
import stripe
from google.cloud import speech
import firebase_admin
import edge_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SetupManager:
    def __init__(self):
        """Initialize setup manager"""
        self.env_path = Path(".env")
        self.required_dirs = [
            "app/data",
            "logs",
            "temp",
            "uploads"
        ]

    def run_setup(self):
        """Run complete setup process"""
        try:
            print("Starting Beaver Interview Trainer setup...")
            
            # Create required directories
            self._create_directories()
            
            # Check environment variables
            self._check_env_file()
            
            # Check dependencies
            self._check_dependencies()
            
            # Test database connection
            self._test_database()
            
            # Test Google Cloud connection
            self._test_google_cloud()
            
            # Test Twilio connection
            self._test_twilio()
            
            # Test Stripe connection
            self._test_stripe()
            
            # Test Edge TTS
            self._test_edge_tts()
            
            # Test Firebase
            self._test_firebase()
            
            print("\nâœ… Setup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            print(f"\nâŒ Setup failed: {str(e)}")
            return False

    def _create_directories(self):
        """Create required directories"""
        print("\nCreating required directories...")
        for dir_path in self.required_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"âœ“ Created {dir_path}")

    def _check_env_file(self):
        """Check and create .env file if needed"""
        print("\nChecking environment variables...")
        
        if not self.env_path.exists():
            print("Creating .env file...")
            env_template = """
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
            """
            with open(self.env_path, 'w') as f:
                f.write(env_template.strip())
            print("Created .env file. Please fill in your credentials.")
            sys.exit(1)
        
        # Load environment variables
        load_dotenv()
        print("âœ“ Environment variables loaded")

    def _check_dependencies(self):
        """Check required Python packages"""
        print("\nChecking dependencies...")
        required_packages = [
            'streamlit',
            'psycopg2-binary',
            'google-cloud-storage',
            'google-cloud-speech',
            'twilio',
            'stripe',
            'edge-tts',
            'firebase-admin',
            'plotly',
            'pandas',
            'numpy',
            'jinja2',
            'python-dotenv'
        ]
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"âœ“ {package} installed")
            except ImportError:
                print(f"âœ— {package} not installed")
                if input(f"Install {package}? (y/n): ").lower() == 'y':
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

    def _test_database(self):
        """Test database connection"""
        print("\nTesting database connection...")
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT'),
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD')
            )
            conn.close()
            print("âœ“ Database connection successful")
        except Exception as e:
            print(f"âœ— Database connection failed: {str(e)}")
            raise

    def _test_google_cloud(self):
        """Test Google Cloud connection"""
        print("\nTesting Google Cloud connection...")
        try:
            # Test Storage
            storage_client = google.cloud.storage.Client()
            storage_client.list_buckets(max_results=1)
            print("âœ“ Google Cloud Storage connection successful")
            
            # Test Speech-to-Text
            speech_client = speech.SpeechClient()
            print("âœ“ Google Cloud Speech-to-Text connection successful")
            
        except Exception as e:
            print(f"âœ— Google Cloud connection failed: {str(e)}")
            raise

    def _test_twilio(self):
        """Test Twilio connection"""
        print("\nTesting Twilio connection...")
        try:
            client = Client(
                os.getenv('TWILIO_ACCOUNT_SID'),
                os.getenv('TWILIO_AUTH_TOKEN')
            )
            client.api.accounts.list(limit=1)
            print("âœ“ Twilio connection successful")
        except Exception as e:
            print(f"âœ— Twilio connection failed: {str(e)}")
            raise

    def _test_stripe(self):
        """Test Stripe connection"""
        print("\nTesting Stripe connection...")
        try:
            stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
            stripe.Account.retrieve()
            print("âœ“ Stripe connection successful")
        except Exception as e:
            print(f"âœ— Stripe connection failed: {str(e)}")
            raise

    def _test_edge_tts(self):
        """Test Edge TTS"""
        print("\nTesting Edge TTS...")
        try:
            import edge_tts
            print("âœ“ Edge TTS available")
        except Exception as e:
            print(f"âœ— Edge TTS test failed: {str(e)}")
            raise

    def _test_firebase(self):
        """Test Firebase connection"""
        print("\nTesting Firebase connection...")
        try:
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
            if not firebase_admin._apps:
                cred = firebase_admin.credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            print("âœ“ Firebase connection successful")
        except Exception as e:
            print(f"âœ— Firebase connection failed: {str(e)}")
            raise

if __name__ == "__main__":
    setup_manager = SetupManager()
    setup_manager.run_setup()