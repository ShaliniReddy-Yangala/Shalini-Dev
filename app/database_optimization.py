"""
Database optimization script for user_role_access table
Adds indexes to improve query performance
"""

from sqlalchemy import text
from app.database import engine, get_db
import logging

logger = logging.getLogger(__name__)

def populate_email_column_in_user_role_access():
    """Populate email column in existing user_role_access records"""
    
    try:
        with engine.connect() as conn:
            # Update email column by joining with users table
            logger.info("Populating email column in user_role_access table")
            conn.execute(text("""
                UPDATE user_role_access 
                SET email = users.email 
                FROM users 
                WHERE user_role_access.user_id = users.id 
                AND user_role_access.email IS NULL
            """))
            
            conn.commit()
            logger.info("Email column populated successfully!")
            
    except Exception as e:
        logger.error(f"Error populating email column: {str(e)}")
        raise

def add_email_column_to_user_role_access():
    """Add email column to user_role_access table for direct email lookups"""
    
    try:
        with engine.connect() as conn:
            # Check if email column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user_role_access' 
                AND column_name = 'email'
            """))
            
            if result.fetchone():
                logger.info("Email column already exists in user_role_access table")
                # Populate the email column for existing records
                populate_email_column_in_user_role_access()
                return
            
            # Add email column
            logger.info("Adding email column to user_role_access table")
            conn.execute(text("""
                ALTER TABLE user_role_access 
                ADD COLUMN email VARCHAR(255)
            """))
            
            # Create index on email column for fast lookups
            logger.info("Creating index on email column")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_role_access_email 
                ON user_role_access(email)
            """))
            
            # Create case-insensitive index for email searches
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_role_access_email_lower 
                ON user_role_access(LOWER(email))
            """))
            
            conn.commit()
            logger.info("Email column and indexes added successfully!")
            
            # Populate the email column for existing records
            populate_email_column_in_user_role_access()
            
    except Exception as e:
        logger.error(f"Error adding email column: {str(e)}")
        raise

def create_user_role_access_indexes():
    """Create indexes for user_role_access table to improve performance"""
    
    indexes = [
        # Index on user_id for faster lookups by user
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_user_id ON user_role_access(user_id)",
        
        # Index on role_template_id for faster lookups by template
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_role_template_id ON user_role_access(role_template_id)",
        
        # Composite index on user_id and role_name for common queries
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_user_role ON user_role_access(user_id, role_name)",
        
        # Index on expiry_date for filtering expired access
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_expiry_date ON user_role_access(expiry_date)",
        
        # Index on created_at for sorting and filtering
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_created_at ON user_role_access(created_at)",
        
        # Index on is_super_admin for filtering admin users
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_super_admin ON user_role_access(is_super_admin)",
        
        # Index on is_unrestricted for filtering unrestricted access
        "CREATE INDEX IF NOT EXISTS idx_user_role_access_unrestricted ON user_role_access(is_unrestricted)"
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                logger.info(f"Creating index: {index_sql}")
                conn.execute(text(index_sql))
                conn.commit()
            
            logger.info("All indexes created successfully!")
            
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise

def create_user_table_indexes():
    """Create indexes for users table to improve by-email endpoint performance"""
    
    indexes = [
        # Index on email for faster email lookups (case-insensitive)
        "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email))",
        
        # Index on email for exact matches
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        
        # Index on name for name-based searches
        "CREATE INDEX IF NOT EXISTS idx_users_name ON users(name)",
        
        # Index on department for filtering
        "CREATE INDEX IF NOT EXISTS idx_users_department ON users(department)"
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                logger.info(f"Creating user table index: {index_sql}")
                conn.execute(text(index_sql))
                conn.commit()
            
            logger.info("All user table indexes created successfully!")
            
    except Exception as e:
        logger.error(f"Error creating user table indexes: {str(e)}")
        raise

def create_candidate_table_indexes():
    """Create indexes for candidates table to improve performance"""
    
    indexes = [
        # Index on email_id for faster email lookups
        "CREATE INDEX IF NOT EXISTS idx_candidates_email_id ON candidates(email_id)",
        
        # Index on candidate_name for name searches
        "CREATE INDEX IF NOT EXISTS idx_candidates_name ON candidates(candidate_name)",
        
        # Index on mobile_no for phone searches
        "CREATE INDEX IF NOT EXISTS idx_candidates_mobile ON candidates(mobile_no)",
        
        # Index on status for status filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status)",
        
        # Index on current_status for status filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_current_status ON candidates(current_status)",
        
        # Index on final_status for status filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_final_status ON candidates(final_status)",
        
        # Index on associated_job_id for job filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(associated_job_id)",
        
        # Index on department for department filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_department ON candidates(department)",
        
        # Index on ta_team for team filtering
        "CREATE INDEX IF NOT EXISTS idx_candidates_ta_team ON candidates(ta_team)",
        
        # Index on created_at for sorting
        "CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON candidates(created_at)",
        
        # Index on application_date for sorting
        "CREATE INDEX IF NOT EXISTS idx_candidates_application_date ON candidates(application_date)"
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                logger.info(f"Creating candidate table index: {index_sql}")
                conn.execute(text(index_sql))
                conn.commit()
            
            logger.info("All candidate table indexes created successfully!")
            
    except Exception as e:
        logger.error(f"Error creating candidate table indexes: {str(e)}")
        raise

def analyze_table_performance():
    """Analyze table performance and provide recommendations"""
    
    try:
        with engine.connect() as conn:
            # Get table statistics
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    attname,
                    n_distinct,
                    correlation
                FROM pg_stats 
                WHERE tablename IN ('user_role_access', 'users', 'candidates')
                ORDER BY tablename, n_distinct DESC
            """))
            
            logger.info("Table statistics for optimized tables:")
            for row in result:
                logger.info(f"Table: {row.tablename}, Column: {row.attname}, Distinct values: {row.n_distinct}, Correlation: {row.correlation}")
                
    except Exception as e:
        logger.error(f"Error analyzing table performance: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting database optimization...")
    add_email_column_to_user_role_access()
    create_user_role_access_indexes()
    create_user_table_indexes()
    create_candidate_table_indexes()
    analyze_table_performance()
    logger.info("Database optimization completed!")

