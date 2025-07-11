"""
Configuration management for MailAssistant
"""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional
import os


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="Database URL")
    pool_size: int = Field(20, description="Connection pool size")
    max_overflow: int = Field(30, description="Max overflow connections")


class LLMConfig(BaseModel):
    """LLM configuration"""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    default_provider: str = Field("openai", description="Default LLM provider")
    default_model: str = Field("gpt-4o", description="Default LLM model")


class GoogleOAuthConfig(BaseModel):
    """Google OAuth configuration"""
    client_id: str = Field(..., description="Google OAuth client ID")
    client_secret: str = Field(..., description="Google OAuth client secret")
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str = Field(..., description="Secret key for JWT")
    encryption_key: str = Field(..., description="Encryption key for sensitive data")
    jwt_algorithm: str = Field("HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(1440, description="JWT expiration in minutes")


class AppConfig(BaseModel):
    """Application configuration"""
    name: str = Field("MailAssistant", description="Application name")
    version: str = Field("1.0.0", description="Application version")
    debug: bool = Field(False, description="Debug mode")
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")


class RedisConfig(BaseModel):
    """Redis configuration"""
    url: str = Field("redis://localhost:6379/0", description="Redis URL")


class LogConfig(BaseModel):
    """Logging configuration"""
    level: str = Field("INFO", description="Log level")
    file: Optional[str] = Field(None, description="Log file path")


class TaskConfig(BaseModel):
    """Task configuration"""
    retry_times: int = Field(3, description="Task retry times")
    retry_delay: int = Field(60, description="Task retry delay in seconds")
    daily_report_default_time: str = Field("08:00", description="Default daily report time")


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(30, env="DATABASE_MAX_OVERFLOW")
    
    # LLM
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    gemini_api_key: Optional[str] = Field(None, env="GEMINI_API_KEY")
    default_llm_provider: str = Field("openai", env="DEFAULT_LLM_PROVIDER")
    default_llm_model: str = Field("gpt-4o", env="DEFAULT_LLM_MODEL")
    
    # Google OAuth
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(..., env="GOOGLE_REDIRECT_URI")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(1440, env="JWT_EXPIRE_MINUTES")
    
    # Application
    app_name: str = Field("MailAssistant", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # Tasks
    task_retry_times: int = Field(3, env="TASK_RETRY_TIMES")
    task_retry_delay: int = Field(60, env="TASK_RETRY_DELAY")
    daily_report_default_time: str = Field("08:00", env="DAILY_REPORT_DEFAULT_TIME")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(
            url=self.database_url,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow
        )
    
    @property
    def llm(self) -> LLMConfig:
        return LLMConfig(
            openai_api_key=self.openai_api_key,
            anthropic_api_key=self.anthropic_api_key,
            gemini_api_key=self.gemini_api_key,
            default_provider=self.default_llm_provider,
            default_model=self.default_llm_model
        )
    
    @property
    def google_oauth(self) -> GoogleOAuthConfig:
        return GoogleOAuthConfig(
            client_id=self.google_client_id,
            client_secret=self.google_client_secret,
            redirect_uri=self.google_redirect_uri
        )
    
    @property
    def security(self) -> SecurityConfig:
        return SecurityConfig(
            secret_key=self.secret_key,
            encryption_key=self.encryption_key,
            jwt_algorithm=self.jwt_algorithm,
            jwt_expire_minutes=self.jwt_expire_minutes
        )
    
    @property
    def app(self) -> AppConfig:
        return AppConfig(
            name=self.app_name,
            version=self.app_version,
            debug=self.debug,
            host=self.host,
            port=self.port
        )
    
    @property
    def redis(self) -> RedisConfig:
        return RedisConfig(url=self.redis_url)
    
    @property
    def logging(self) -> LogConfig:
        return LogConfig(
            level=self.log_level,
            file=self.log_file
        )
    
    @property
    def tasks(self) -> TaskConfig:
        return TaskConfig(
            retry_times=self.task_retry_times,
            retry_delay=self.task_retry_delay,
            daily_report_default_time=self.daily_report_default_time
        )


# Global settings instance
settings = Settings()