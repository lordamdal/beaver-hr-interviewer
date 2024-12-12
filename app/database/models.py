# app/database/models.py

from datetime import datetime
from typing import Dict, List, Optional, Any
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSON, UUID
import uuid
from app.config.settings import settings, get_db_url

# Create database engine and session
engine = sa.create_engine(get_db_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = sa.Column(sa.String(100), nullable=False)
    phone = sa.Column(sa.String(20), unique=True, nullable=False)
    email = sa.Column(sa.String(255), unique=True, nullable=True)
    subscription_plan = sa.Column(sa.String(50), default="free")
    subscription_end_date = sa.Column(sa.DateTime, nullable=True)
    interviews_remaining = sa.Column(sa.Integer, default=1)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def create(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        db = next(get_db())
        user = cls(**data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return cls.to_dict(user)

    @classmethod
    def get_by_phone(cls, phone: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        db = next(get_db())
        user = db.query(cls).filter(cls.phone == phone).first()
        return cls.to_dict(user) if user else None

    @staticmethod
    def to_dict(user) -> Dict[str, Any]:
        """Convert user object to dictionary"""
        if not user:
            return None
        return {
            'id': str(user.id),
            'name': user.name,
            'phone': user.phone,
            'email': user.email,
            'subscription_plan': user.subscription_plan,
            'subscription_end_date': user.subscription_end_date,
            'interviews_remaining': user.interviews_remaining,
            'created_at': user.created_at,
            'updated_at': user.updated_at
        }

class Resume(Base):
    __tablename__ = "resumes"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False)
    file_path = sa.Column(sa.String(255), nullable=False)
    parsed_data = sa.Column(JSON, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

class Interview(Base):
    __tablename__ = "interviews"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False)
    resume_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey('resumes.id'), nullable=False)
    company_name = sa.Column(sa.String(100), nullable=True)
    company_website = sa.Column(sa.String(255), nullable=True)
    job_description = sa.Column(sa.Text, nullable=True)
    total_score = sa.Column(sa.Integer, nullable=True)
    feedback = sa.Column(JSON, nullable=True)
    recording_url = sa.Column(sa.String(255), nullable=True)
    transcript = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)

class AdminSettings(Base):
    __tablename__ = "admin_settings"

    id = sa.Column(sa.Integer, primary_key=True)
    setting_key = sa.Column(sa.String(100), unique=True, nullable=False)
    setting_value = sa.Column(sa.String(500), nullable=True)
    is_sensitive = sa.Column(sa.Boolean, default=False)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)

class DatabaseManager:
    @staticmethod
    def test_connection() -> bool:
        """Test database connection"""
        try:
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            return False

    @staticmethod
    def create_tables():
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=engine)
            return True
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
            return False

    @staticmethod
    def get_table_names() -> List[str]:
        """Get all table names"""
        return engine.table_names()

if __name__ == "__main__":
    # When run directly, initialize the database
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    
    # Test connection
    db_manager = DatabaseManager()
    if db_manager.test_connection():
        print("Database connection successful!")
        print(f"Available tables: {db_manager.get_table_names()}")
    else:
        print("Database connection failed!")