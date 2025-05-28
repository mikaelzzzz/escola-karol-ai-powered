import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    FLEXGE_API_BASE: str = os.getenv("FLEXGE_API_BASE", "https://partner-api.flexge.com/external")
    FLEXGE_API_KEY: str = os.getenv("FLEXGE_API_KEY")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER: str = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD")
    ZAIA_API_KEY: str = os.getenv("ZAIA_API_KEY")
    ZAIA_API_URL: str = os.getenv("ZAIA_API_URL", "https://api.zaia.app/v1.1/api")
    ZAIA_AGENT_ID: int = int(os.getenv("ZAIA_AGENT_ID", "34790"))
    ASAAS_API_KEY: str = os.getenv("ASAAS_API_KEY")
    ASAAS_BASE: str = os.getenv("ASAAS_BASE", "https://api.asaas.com/v3")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "ie5yJLYeLpsuijLaojmF")
    ZAPI_INSTANCE_ID: str = os.getenv("ZAPI_INSTANCE_ID")
    ZAPI_TOKEN: str = os.getenv("ZAPI_TOKEN")
    ZAPI_SECURITY_TOKEN: str = os.getenv("ZAPI_SECURITY_TOKEN")
    NOTION_API_KEY: str = os.getenv("NOTION_API_KEY")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID")
    ALLOWED_EXTENSIONS: set = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE: int = 5 * 1024 * 1024
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    class Config:
        env_file = ".env"

settings = Settings() 