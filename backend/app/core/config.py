"""
애플리케이션 설정 모듈
환경 변수를 통해 설정값을 관리합니다.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """애플리케이션 설정"""
    
    # 환경 설정
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # 데이터베이스 설정
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./users.db")
    
    # CORS 설정
    CORS_ORIGINS: List[str] = [
        origin.strip() 
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    ]
    
    # API 설정
    API_HOST: str = os.getenv("API_HOST", "localhost")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Typesense 설정
    TYPESENSE_HOST: str = os.getenv("TYPESENSE_HOST", "localhost")
    TYPESENSE_PORT: int = int(os.getenv("TYPESENSE_PORT", "8108"))
    TYPESENSE_API_KEY: str = os.getenv("TYPESENSE_API_KEY", "xyz")
    
    # OpenAI 설정
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")


settings = Settings()
print("CORS_ORIGINS:", settings.CORS_ORIGINS)