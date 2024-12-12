# Beaver Job Interview Trainer

A Python-based SaaS platform built with Streamlit to help users practice job interviews using an AI conversational agent. The platform simulates phone interviews via the Twilio API and delivers detailed performance reports.

---

## 📑 Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Project Structure](#project-structure)
8. [API Documentation](#api-documentation)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)
12. [Support](#support)

---

## ✨ Features
- **AI-powered interview simulation**
- **Real-time phone interviews** via Twilio
- Speech-to-text and text-to-speech integration
- Detailed performance analytics
- Resume parsing and analysis
- Customizable interview scenarios
- Premium subscription features
- Admin dashboard
- Support system with email notifications

---

## 📋 Prerequisites
- Python 3.8+
- PostgreSQL 13+
- Google Cloud Platform account
- Twilio account
- Stripe account (for payments)
- Edge-TTS
- Firebase account (for notifications)

---

## 🛠️ Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/beaver-interview-trainer.git
    cd beaver-interview-trainer
    ```

2. **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Install additional system dependencies**:
    - **For Ubuntu/Debian**:
        ```bash
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio
        ```
    - **For Windows**:
        - Install PyAudio manually if needed.

---

## ⚙️ Configuration

1. **Create a `.env` file** in the project root with the following:
    ```plaintext
    # App Settings
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
    ```

2. **Set up Google Cloud credentials**:
    - Create a service account in Google Cloud Console.
    - Download the credentials JSON file.
    - Set the `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`.

3. **Initialize the database**:
    ```bash
    python scripts/init_db.py
    ```

---

## 🚀 Running the Application

1. Start the main application:
    ```bash
    streamlit run app/main.py
    ```

2. Access the admin panel at:
    - URL: `http://localhost:8501/godfather`
    - Default credentials:
        - **Username**: admin
        - **Password**: (check `settings.py`)

---

## 🧪 Testing

1. Run unit tests:
    ```bash
    pytest tests/
    ```

2. Test individual components:
    - **Interview System**:
        ```bash
        python -m pytest tests/test_interview.py
        ```
    - **Payment System**:
        ```bash
        python -m pytest tests/test_payment.py
        ```
    - **Support System**:
        ```bash
        python -m pytest tests/test_support.py
        ```

---

## 🗂️ Project Structure
```plaintext
app/
├── main.py
├── admin/
│   ├── dashboard.py
│   └── setup.py
├── auth/
│   └── authentication.py
├── components/
│   ├── landing_page.py
│   ├── interview.py
│   ├── report.py
│   ├── profile.py
│   ├── support.py
│   ├── analytics.py
│   └── feedback.py
├── config/
│   └── settings.py
├── database/
│   ├── models.py
│   └── operations.py
├── services/
│   ├── llm_service.py
│   ├── storage_service.py
│   ├── twilio_service.py
│   ├── stt_service.py
│   ├── tts_service.py
│   ├── payment_service.py
│   ├── email_service.py
│   └── notification_service.py
├── utils/
│   ├── helpers.py
│   ├── chart_helpers.py
│   └── content_helpers.py
└── templates/
    └── email/
        ├── base.html
        ├── welcome.html
```
## 📜 API Documentation
```plaintext

Twilio Integration
Webhook URL: /api/twilio/webhook
Status Callbacks: /api/twilio/status
Recording Callbacks: /api/twilio/recording
Stripe Integration
Webhook URL: /api/stripe/webhook
Success URL: /subscription/success
Cancel URL: /subscription/cancel
```

##❓ Troubleshooting
Common Issues
Database Connection:
```bash
python scripts/test_db_connection.py
```
Audio Issues:
Check microphone permissions.
Verify audio device settings.
Test with:
```bash
python scripts/test_audio.py
```
API Integration:
Verify API keys in the admin panel.
Check webhook configurations.
Monitor logs in logs/app.log.

##🤝 Contributing
Fork the repository.
Create a feature branch.
Commit changes.
Push to the branch.
Create a Pull Request.
##🛡️ License
MIT License.

##📧 Support
For support, email support@beaverinterviews.com or create an issue in the repository.