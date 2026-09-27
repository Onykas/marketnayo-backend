import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    app_name: str = "MarketNaYo"
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost/marketnayo")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
    twilio_sid: str = os.getenv("TWILIO_SID", "")
    twilio_token: str = os.getenv("TWILIO_TOKEN", "")
    twilio_from: str = os.getenv("TWILIO_FROM", "")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

settings = Settings()