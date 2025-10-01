from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging
from app.config import DATABASE_URI, S3_BASE_URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the database URI from environment variables
DATABASE_URL = DATABASE_URI

# Validate DATABASE_URL
if not DATABASE_URL:
    logger.warning("DATABASE_URI environment variable is not set!")
    logger.info("Falling back to local SQLite database for development")
    DATABASE_URL = "sqlite:///./hrms_local.db"
else:
    logger.info(f"Using database URI: {DATABASE_URL}")

logger.info(f"Attempting to connect to database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

try:
    # Create engine for database connection with optimized pool configuration
    if DATABASE_URL.startswith("sqlite"):
        # SQLite configuration
        engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False}  # Only needed for SQLite
        )
    else:
        # PostgreSQL configuration
        engine = create_engine(
            DATABASE_URL,
            echo=False,  # Set to False in production to reduce logging overhead
            pool_size=10,  # Increased to handle more concurrent requests
            max_overflow=20,  # Increased overflow capacity
            pool_timeout=30,  # Wait time for getting a connection from pool
            pool_recycle=1800,  # Recycle connections after 30 minutes of inactivity
            pool_pre_ping=True,  # Ensure connections are alive before using them
            # Force PostgreSQL to use COMMIT or ROLLBACK to end transactions properly
            isolation_level="AUTOCOMMIT",
            # Add connection arguments for better error handling
            connect_args={
                "connect_timeout": 10,  # 10 second connection timeout
            }
        )
    
    # Test the connection only in non-serverless environments
    # In serverless environments, we'll test the connection when actually needed
    import os
    if not os.environ.get('VERCEL'):  # Only test connection if not on Vercel
        try:
            logger.info("Testing database connection...")
            with engine.connect() as conn:
                logger.info("Database connection successful!")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            logger.error("Please check your DATABASE_URI and network connectivity")
            # Don't raise the exception in serverless environments
            if not os.environ.get('VERCEL'):
                raise
    else:
        logger.info("Skipping database connection test in serverless environment")
        
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    logger.error("Please check your DATABASE_URI configuration")
    raise

# Session local for handling connections
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Modified to work directly with FastAPI's dependency system
def get_db():
    """
    Database session dependency for FastAPI.
    Usage:
        @app.get("/items/")
        def read_items(db = Depends(get_db)):
            # your database operations
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# Remove the get_db_dependency function since it's redundant now
# The get_db function now serves both purposes
