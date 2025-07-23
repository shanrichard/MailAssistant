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




class LogConfig(BaseModel):
    """Logging configuration"""
    level: str = Field("INFO", description="Log level")
    file: Optional[str] = Field(None, description="Log file path")


class TaskConfig(BaseModel):
    """Task configuration"""
    retry_times: int = Field(3, description="Task retry times")
    retry_delay: int = Field(60, description="Task retry delay in seconds")
    daily_report_default_time: str = Field("08:00", description="Default daily report time")


class AgentConfig(BaseModel):
    """Agent configuration"""
    # EmailProcessor Agent配置
    email_processor_timeout: int = Field(300, description="EmailProcessor timeout in seconds")
    email_processor_max_retries: int = Field(3, description="EmailProcessor max retries")
    email_processor_default_model: str = Field("gpt-4o", description="EmailProcessor default model")
    email_processor_temperature: float = Field(0.1, description="EmailProcessor temperature")
    
    # ConversationHandler Agent配置
    conversation_handler_timeout: int = Field(180, description="ConversationHandler timeout in seconds")
    conversation_handler_max_retries: int = Field(2, description="ConversationHandler max retries")
    conversation_handler_default_model: str = Field("gpt-4o", description="ConversationHandler default model")
    conversation_handler_temperature: float = Field(0.3, description="ConversationHandler temperature")
    conversation_handler_session_timeout: int = Field(3600, description="ConversationHandler session timeout in seconds")
    
    # 消息裁剪配置
    message_pruning_enabled: bool = Field(True, description="Enable message pruning")
    max_messages_count: int = Field(50, description="Maximum number of messages to keep")
    max_tokens_count: int = Field(3000, description="Maximum token count for messages")
    pruning_strategy: str = Field("count", description="Pruning strategy: 'count' or 'tokens'")
    
    # 通用Agent配置
    agent_tool_timeout: int = Field(60, description="Agent tool execution timeout in seconds")
    agent_max_concurrent_tasks: int = Field(5, description="Maximum concurrent agent tasks")
    agent_memory_size: int = Field(50, description="Agent conversation memory size")
    
    # WebSocket配置
    websocket_heartbeat_interval: int = Field(30, description="WebSocket heartbeat interval in seconds")
    websocket_max_connections_per_user: int = Field(3, description="Maximum WebSocket connections per user")
    
    # 缓存配置
    preference_cache_ttl: int = Field(300, description="User preference cache TTL in seconds")
    report_cache_ttl: int = Field(900, description="Daily report cache TTL in seconds")


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
    environment: str = Field("production", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(None, env="LOG_FILE")
    
    # Tasks
    task_retry_times: int = Field(3, env="TASK_RETRY_TIMES")
    task_retry_delay: int = Field(60, env="TASK_RETRY_DELAY")
    daily_report_default_time: str = Field("08:00", env="DAILY_REPORT_DEFAULT_TIME")
    
    # Agent配置
    email_processor_timeout: int = Field(300, env="EMAIL_PROCESSOR_TIMEOUT")
    email_processor_max_retries: int = Field(3, env="EMAIL_PROCESSOR_MAX_RETRIES")
    email_processor_default_model: str = Field("gpt-4o", env="EMAIL_PROCESSOR_DEFAULT_MODEL")
    email_processor_temperature: float = Field(0.1, env="EMAIL_PROCESSOR_TEMPERATURE")
    
    conversation_handler_timeout: int = Field(180, env="CONVERSATION_HANDLER_TIMEOUT")
    conversation_handler_max_retries: int = Field(2, env="CONVERSATION_HANDLER_MAX_RETRIES")
    conversation_handler_default_model: str = Field("gpt-4o", env="CONVERSATION_HANDLER_DEFAULT_MODEL")
    conversation_handler_temperature: float = Field(0.3, env="CONVERSATION_HANDLER_TEMPERATURE")
    conversation_handler_session_timeout: int = Field(3600, env="CONVERSATION_HANDLER_SESSION_TIMEOUT")
    
    # 消息裁剪配置
    message_pruning_enabled: bool = Field(True, env="MESSAGE_PRUNING_ENABLED")
    max_messages_count: int = Field(50, env="MAX_MESSAGES_COUNT")
    max_tokens_count: int = Field(3000, env="MAX_TOKENS_COUNT")
    pruning_strategy: str = Field("count", env="PRUNING_STRATEGY")
    
    agent_tool_timeout: int = Field(60, env="AGENT_TOOL_TIMEOUT")
    agent_max_concurrent_tasks: int = Field(5, env="AGENT_MAX_CONCURRENT_TASKS")
    agent_memory_size: int = Field(50, env="AGENT_MEMORY_SIZE")
    
    websocket_heartbeat_interval: int = Field(30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    websocket_max_connections_per_user: int = Field(3, env="WEBSOCKET_MAX_CONNECTIONS_PER_USER")
    
    preference_cache_ttl: int = Field(300, env="PREFERENCE_CACHE_TTL")
    report_cache_ttl: int = Field(900, env="REPORT_CACHE_TTL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量
    
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
    
    @property
    def agents(self) -> AgentConfig:
        return AgentConfig(
            email_processor_timeout=self.email_processor_timeout,
            email_processor_max_retries=self.email_processor_max_retries,
            email_processor_default_model=self.email_processor_default_model,
            email_processor_temperature=self.email_processor_temperature,
            
            conversation_handler_timeout=self.conversation_handler_timeout,
            conversation_handler_max_retries=self.conversation_handler_max_retries,
            conversation_handler_default_model=self.conversation_handler_default_model,
            conversation_handler_temperature=self.conversation_handler_temperature,
            conversation_handler_session_timeout=self.conversation_handler_session_timeout,
            
            message_pruning_enabled=self.message_pruning_enabled,
            max_messages_count=self.max_messages_count,
            max_tokens_count=self.max_tokens_count,
            pruning_strategy=self.pruning_strategy,
            
            agent_tool_timeout=self.agent_tool_timeout,
            agent_max_concurrent_tasks=self.agent_max_concurrent_tasks,
            agent_memory_size=self.agent_memory_size,
            
            websocket_heartbeat_interval=self.websocket_heartbeat_interval,
            websocket_max_connections_per_user=self.websocket_max_connections_per_user,
            
            preference_cache_ttl=self.preference_cache_ttl,
            report_cache_ttl=self.report_cache_ttl
        )


# Global settings instance
settings = Settings()