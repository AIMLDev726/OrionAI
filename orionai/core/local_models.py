"""
Local AI Models Support
=======================

Support for local AI models via Ollama, LMStudio, and other local inference engines.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocalModelInfo:
    """Information about a local model."""
    name: str
    provider: str  # ollama, lmstudio, etc.
    endpoint: str
    size: Optional[str] = None
    description: Optional[str] = None
    available: bool = False


class OllamaProvider:
    """Ollama local AI provider."""
    
    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3"):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models."""
        if not self.available:
            return []
        
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
        
        return []
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Ollama."""
        if not self.available:
            raise Exception("Ollama is not available")
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "num_predict": kwargs.get("max_tokens", 2000),
                    "top_k": kwargs.get("top_k", 40),
                    "top_p": kwargs.get("top_p", 0.9),
                }
            }
            
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', '')
            else:
                raise Exception(f"Ollama request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise


class LMStudioProvider:
    """LM Studio local AI provider."""
    
    def __init__(self, endpoint: str = "http://localhost:1234", model: str = "local-model"):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if LM Studio is running and accessible."""
        try:
            response = requests.get(f"{self.endpoint}/v1/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available LM Studio models."""
        if not self.available:
            return []
        
        try:
            response = requests.get(f"{self.endpoint}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
        except Exception as e:
            logger.error(f"Error listing LM Studio models: {e}")
        
        return []
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using LM Studio."""
        if not self.available:
            raise Exception("LM Studio is not available")
        
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2000),
                "top_p": kwargs.get("top_p", 0.9),
                "stream": False
            }
            
            response = requests.post(
                f"{self.endpoint}/v1/chat/completions",
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            
            if response.status_code == 200:
                data = response.json()
                choices = data.get('choices', [])
                if choices:
                    return choices[0]['message']['content']
                return ""
            else:
                raise Exception(f"LM Studio request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"LM Studio generation error: {e}")
            raise


class OpenAICompatibleProvider:
    """Generic OpenAI-compatible API provider for local models."""
    
    def __init__(self, endpoint: str, model: str = "local-model", api_key: str = "local"):
        self.endpoint = endpoint.rstrip('/')
        self.model = model
        self.api_key = api_key
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if the API is available."""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.endpoint}/v1/models", headers=headers, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        if not self.available:
            return []
        
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.endpoint}/v1/models", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
        except Exception as e:
            logger.error(f"Error listing models: {e}")
        
        return []
    
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI-compatible API."""
        if not self.available:
            raise Exception("Local API is not available")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2000),
                "stream": False
            }
            
            response = requests.post(
                f"{self.endpoint}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=kwargs.get("timeout", 120)
            )
            
            if response.status_code == 200:
                data = response.json()
                choices = data.get('choices', [])
                if choices:
                    return choices[0]['message']['content']
                return ""
            else:
                raise Exception(f"API request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Local API generation error: {e}")
            raise


class LocalModelManager:
    """Manager for local AI models."""
    
    def __init__(self):
        self.providers = {
            'ollama': OllamaProvider(),
            'lmstudio': LMStudioProvider(),
        }
        self.custom_providers = {}
    
    def add_custom_provider(self, name: str, endpoint: str, model: str = "local-model", api_key: str = "local"):
        """Add a custom OpenAI-compatible provider."""
        self.custom_providers[name] = OpenAICompatibleProvider(endpoint, model, api_key)
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        available = []
        
        for name, provider in self.providers.items():
            if provider.available:
                available.append(name)
        
        for name, provider in self.custom_providers.items():
            if provider.available:
                available.append(name)
        
        return available
    
    def get_provider(self, name: str):
        """Get a specific provider."""
        if name in self.providers:
            return self.providers[name]
        elif name in self.custom_providers:
            return self.custom_providers[name]
        else:
            raise ValueError(f"Provider '{name}' not found")
    
    def list_all_models(self) -> Dict[str, List[LocalModelInfo]]:
        """List all available models from all providers."""
        all_models = {}
        
        for name, provider in {**self.providers, **self.custom_providers}.items():
            if provider.available:
                try:
                    models = provider.list_models()
                    model_infos = []
                    
                    for model in models:
                        if name == 'ollama':
                            model_info = LocalModelInfo(
                                name=model.get('name', ''),
                                provider=name,
                                endpoint=provider.endpoint,
                                size=model.get('size'),
                                description=model.get('details', {}).get('family', ''),
                                available=True
                            )
                        else:
                            model_info = LocalModelInfo(
                                name=model.get('id', ''),
                                provider=name,
                                endpoint=provider.endpoint,
                                description=model.get('description', ''),
                                available=True
                            )
                        
                        model_infos.append(model_info)
                    
                    all_models[name] = model_infos
                    
                except Exception as e:
                    logger.error(f"Error listing models for {name}: {e}")
        
        return all_models
    
    def test_provider(self, provider_name: str, model_name: str = None) -> bool:
        """Test a provider with a simple prompt."""
        try:
            provider = self.get_provider(provider_name)
            
            if model_name:
                provider.model = model_name
            
            test_prompt = "Hello! Please respond with 'Hello from local AI!'"
            response = provider.generate(test_prompt, temperature=0.1, max_tokens=50)
            
            return bool(response and len(response.strip()) > 0)
            
        except Exception as e:
            logger.error(f"Provider test failed: {e}")
            return False
