import os

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except ImportError:
        class BaseSettings:
            pass

class Settings(BaseSettings):
    PROJECT_NAME: str = "InnoCart V2 Backend"
    VERSION: str = "2.0.0"
    API_PREFIX: str = "/api"

    # Database Settings (Default: Supabase IPv4 Transaction Pooler Port 6543)
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "aws-0-ap-southeast-2.pooler.supabase.com")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "6543"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "postgres.uczulnmdbsslqqgxnbyd")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "Somanathi@7463")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "postgres")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    # Redis Settings
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # Security
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-innocart-v2")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Payment Gateway
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID", "rzp_test_innocart123")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET", "secret_innocart_key")
    USE_MOCK_PAYMENTS: bool = os.getenv("USE_MOCK_PAYMENTS", "true").lower() in ("true", "1")

    # Real Twilio SMS Integration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Session TTL
    SESSION_TTL_SECONDS: int = 3600

settings = Settings()
