import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuration settings for the application.
    Loads environment variables from a .env file.
    """
    GROQ_API_KEY: str = "" # Keep this empty string for Canvas environment; it's injected automatically.

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
# DEBUG PRINT: Verify what API key is being loaded by pydantic-settings
print(f"\n--- DEBUG: Configured GROQ_API_KEY in config.py: '{settings.GROQ_API_KEY[:5]}...{settings.GROQ_API_KEY[-5:]}' (truncated for security) ---")
    