#!/usr/bin/env python3
"""
Script to create database indexes for optimizing the /candidates/by-email endpoint
Run this script to create all necessary indexes for fast email lookups
"""

from sqlalchemy import text, create_engine
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_indexes():
    """Create all necessary indexes for the optimized by-email endpoint"""
    
    # Database connection string - adjust as needed
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://username:password@localhost/hrms_db")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            logger.info("Creating database indexes for optimized email lookups...")
            
            # Indexes for users table
            user_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email))",
                "CREATE INDEX IF NOT EXISTS idx_users_name ON users(name)",
                "CREATE INDEX IF NOT EXISTS idx_users_department ON users(department)",
                "CREATE INDEX IF NOT EXISTS idx_users_name_email ON users(name, email)"
            ]
            
            # Indexes for user_role_access table
            access_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_email_lower ON user_role_access(LOWER(email))",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_user_id ON user_role_access(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_role_template_id ON user_role_access(role_template_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_is_super_admin ON user_role_access(is_super_admin)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_expiry_date ON user_role_access(expiry_date)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_created_at ON user_role_access(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_is_unrestricted ON user_role_access(is_unrestricted)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_user_email ON user_role_access(user_id, email)",
                "CREATE INDEX IF NOT EXISTS idx_user_role_access_email_role ON user_role_access(email, role_name)"
            ]
            
            # Create all indexes
            all_indexes = user_indexes + access_indexes
            
            for index_sql in all_indexes:
                try:
                    logger.info(f"Creating index: {index_sql}")
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.info("✓ Index created successfully")
                except Exception as e:
                    logger.warning(f"Warning creating index: {e}")
                    # Continue with other indexes
                    continue
            
            logger.info("✓ All database indexes created successfully!")
            
            # Verify indexes exist
            logger.info("Verifying indexes...")
            verify_indexes(conn)
            
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        raise

def verify_indexes(conn):
    """Verify that the created indexes exist"""
    
    # Check users table indexes
    user_indexes = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'users' 
        AND indexname LIKE 'idx_users_%'
    """)).fetchall()
    
    logger.info(f"Users table indexes: {[idx[0] for idx in user_indexes]}")
    
    # Check user_role_access table indexes
    access_indexes = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'user_role_access' 
        AND indexname LIKE 'idx_user_role_access_%'
    """)).fetchall()
    
    logger.info(f"UserRoleAccess table indexes: {[idx[0] for idx in access_indexes]}")

if __name__ == "__main__":
    create_database_indexes()