import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DB_URL: str = os.environ.get("DB_URL")
    API_URL: str = os.environ.get("API_URL")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN")

    class Config:
        env_file = ".env"
        extra = "allow"
        env_file_encoding = "utf-8"


# Initialize the settings
config = Settings()