"""
Configuration module for loading environment variables from OS environment
"""
import os
from typing import Optional

class Config:
    """Configuration class to load environment variables from OS environment"""
    
    @staticmethod
    def get_env_var(key: str, default: Optional[str] = None) -> str:
        """Get environment variable from OS environment with fallback"""
        value = os.environ.get(key, default)
        if value is None:
            raise ValueError(f"Environment variable {key} is required but not set")
        return value
    
    @staticmethod
    def get_env_var_optional(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get optional environment variable from OS environment"""
        return os.environ.get(key, default)

# Create a global config instance
config = Config()

# AWS Configuration
AWS_REGION = config.get_env_var("AWS_REGION", "ap-south-2")
S3_BUCKET = config.get_env_var("S3_BUCKET", "upload-media00")
AWS_ACCESS_KEY_ID = config.get_env_var("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = config.get_env_var("AWS_SECRET_ACCESS_KEY")
AWS_ACCESS_KEY_ID1 = config.get_env_var("AWS_ACCESS_KEY_ID1")
AWS_SECRET_ACCESS_KEY1 = config.get_env_var("AWS_SECRET_ACCESS_KEY1")

# Database Configuration
DATABASE_URI = config.get_env_var("DATABASE_URI")
S3_BASE_URL = config.get_env_var("S3_BASE_URL", "https://storage-bucket.s3.amazonaws.com")

# Supabase Configuration
SUPABASE_URL = config.get_env_var("SUPABASE_URL")
SUPABASE_ANON_KEY = config.get_env_var("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = config.get_env_var("SUPABASE_SERVICE_ROLE_KEY")

# Email Configuration
SENDER_EMAIL = config.get_env_var("SENDER_EMAIL", "hr@vaics-consulting.com")

# Frontend Configuration
FRONTEND_URL = config.get_env_var("FRONTEND_URL", "https://dev.hrms.vaics-consulting.com")

# Portal Configuration (for backward compatibility)
PORTAL_SECRET = config.get_env_var("PORTAL_SECRET", "your-secret-key-here-must-be-at-least-32-characters-long")
PORTAL_URL = config.get_env_var("PORTAL_URL", "https://dev.portal.vaics-consulting.com")

# SSO Configuration
ENVIRONMENT = config.get_env_var_optional("ENVIRONMENT") 