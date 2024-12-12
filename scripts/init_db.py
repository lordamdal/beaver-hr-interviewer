# scripts/init_db.py

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


from app.config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self):
        """Initialize database setup"""
        self.db_params = {
            'host': settings.DB_HOST,
            'port': settings.DB_PORT,
            'user': settings.DB_USER,
            'password': settings.DB_PASSWORD.get_secret_value(),
            'dbname': settings.DB_NAME
        }

    def init_database(self):
        """Initialize the database"""
        try:
            # First, connect to PostgreSQL without specifying a database
            conn = psycopg2.connect(
                host=self.db_params['host'],
                port=self.db_params['port'],
                user=self.db_params['user'],
                password=self.db_params['password']
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()

            # Create database if it doesn't exist
            cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
                       (self.db_params['dbname'],))
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {self.db_params['dbname']}")
                logger.info(f"Database {self.db_params['dbname']} created successfully")
            
            cur.close()
            conn.close()

            # Connect to the new database and create tables
            self._create_tables()
            
            # Initialize default data
            self._init_default_data()

            logger.info("Database initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return False

    def _create_tables(self):
        """Create database tables"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Create tables
            cur.execute("""
                -- Users table
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    phone VARCHAR(20) UNIQUE,
                    password_hash VARCHAR(255),
                    subscription_plan VARCHAR(50) DEFAULT 'free',
                    subscription_end_date TIMESTAMP,
                    interviews_remaining INTEGER DEFAULT 1,
                    stripe_customer_id VARCHAR(255),
                    stripe_subscription_id VARCHAR(255),
                    avatar_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Resumes table
                CREATE TABLE IF NOT EXISTS resumes (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    file_path TEXT NOT NULL,
                    parsed_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Interviews table
                CREATE TABLE IF NOT EXISTS interviews (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    resume_id UUID REFERENCES resumes(id),
                    company_name VARCHAR(100),
                    company_website TEXT,
                    job_description TEXT,
                    total_score INTEGER,
                    feedback JSONB,
                    recording_url TEXT,
                    transcript TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Support Tickets table
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    category VARCHAR(50) NOT NULL,
                    subject VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    priority VARCHAR(20) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Ticket Updates table
                CREATE TABLE IF NOT EXISTS ticket_updates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    ticket_id UUID REFERENCES support_tickets(id),
                    user_id UUID REFERENCES users(id),
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Notifications table
                CREATE TABLE IF NOT EXISTS notifications (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    type VARCHAR(50) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Admin Settings table
                CREATE TABLE IF NOT EXISTS admin_settings (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    setting_key VARCHAR(100) UNIQUE NOT NULL,
                    setting_value TEXT,
                    is_sensitive BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Feedback table
                CREATE TABLE IF NOT EXISTS feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id),
                    interview_id UUID REFERENCES interviews(id),
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Create updated_at triggers
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';

                CREATE TRIGGER update_users_updated_at
                    BEFORE UPDATE ON users
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();

                CREATE TRIGGER update_support_tickets_updated_at
                    BEFORE UPDATE ON support_tickets
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)

            conn.commit()
            logger.info("Database tables created successfully")

        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
        finally:
            cur.close()
            conn.close()

    def _init_default_data(self):
        """Initialize default data"""
        try:
            conn = psycopg2.connect(**self.db_params)
            cur = conn.cursor()

            # Insert default admin settings
            cur.execute("""
                INSERT INTO admin_settings (setting_key, setting_value, is_sensitive)
                VALUES 
                    ('maintenance_mode', 'false', false),
                    ('max_file_size_mb', '10', false),
                    ('default_language', 'en-US', false)
                ON CONFLICT (setting_key) DO NOTHING;
            """)

            conn.commit()
            logger.info("Default data initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing default data: {str(e)}")
            raise
        finally:
            cur.close()
            conn.close()

    def check_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = psycopg2.connect(**self.db_params)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

def main():
    """Main function to initialize database"""
    # Initialize database
    db_init = DatabaseInitializer()
    
    # Test connection
    print("\nTesting database connection...")
    if not db_init.check_connection():
        print("The Database connection failed. Please check your settings.")
        return False

    print("Database connection successful")
    
    # Initialize database
    print("\nInitializing database...")
    if db_init.init_database():
        print("Database initialized successfully")
        return True
    else:
        print("Database initialization failed")
        return False

if __name__ == "__main__":
    main()