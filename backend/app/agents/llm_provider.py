"""
LLM Provider统一管理 - 支持LangChain
"""
from typing import Optional, Dict, Any, List
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain.chat_models.base import BaseChatModel

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class LLMProviderType(str, Enum):
    OPENAI = "openai"

class LLMProviderManager:
    """LLM Provider管理器"""
    
    def __init__(self):
        self._providers: Dict[str, BaseChatModel] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化OpenAI LLM provider"""
        try:
            # OpenAI
            if settings.llm.openai_api_key:
                self._providers[LLMProviderType.OPENAI] = ChatOpenAI(
                    api_key=settings.llm.openai_api_key,
                    model=settings.llm.default_model,
                    temperature=0.1
                )
                logger.info("OpenAI provider initialized")
            else:
                logger.warning("OpenAI API key not configured")
                
        except Exception as e:
            logger.error("Failed to initialize OpenAI provider", error=str(e))
    
    def get_llm(self, provider: str = None, model: str = None, temperature: float = None) -> BaseChatModel:
        """获取LLM实例"""
        provider = provider or settings.llm.default_provider
        
        if provider not in self._providers:
            # 如果指定的provider不可用，使用默认的或第一个可用的
            available_providers = list(self._providers.keys())
            if not available_providers:
                raise RuntimeError("No LLM providers are available")
            
            provider = available_providers[0]
            logger.warning(f"Requested provider not available, using {provider}")
        
        base_llm = self._providers[provider]
        
        # 如果需要自定义参数，创建新实例
        if model or temperature is not None:
            if provider == LLMProviderType.OPENAI:
                return ChatOpenAI(
                    api_key=settings.llm.openai_api_key,
                    model=model or settings.llm.default_model,
                    temperature=temperature if temperature is not None else 0.1
                )
        
        return base_llm
    
    async def generate_with_fallback(self, prompt: str, **kwargs) -> str:
        """使用fallback机制生成响应"""
        providers_to_try = [
            settings.llm.default_provider,
            LLMProviderType.OPENAI
        ]
        
        # 去重并过滤可用的providers
        providers_to_try = list(dict.fromkeys(providers_to_try))
        providers_to_try = [p for p in providers_to_try if p in self._providers]
        
        if not providers_to_try:
            raise RuntimeError("No LLM providers are available")
        
        last_error = None
        
        for provider in providers_to_try:
            try:
                llm = self.get_llm(provider)
                response = await llm.ainvoke(prompt, **kwargs)
                
                # 提取响应内容
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                logger.info("LLM response generated", 
                           provider=provider, 
                           prompt_length=len(prompt),
                           response_length=len(content))
                
                return content
                
            except Exception as e:
                last_error = e
                logger.warning(f"LLM provider {provider} failed", error=str(e))
                continue
        
        # 所有providers都失败了
        logger.error("All LLM providers failed", error=str(last_error))
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    def get_available_providers(self) -> List[str]:
        """获取可用的provider列表"""
        return list(self._providers.keys())
    
    def is_provider_available(self, provider: str) -> bool:
        """检查provider是否可用"""
        return provider in self._providers

# 全局LLM Provider管理器实例
llm_provider_manager = LLMProviderManager()