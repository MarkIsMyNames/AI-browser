import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama") # ollama, openai, azure
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL_ID: str = os.getenv("OLLAMA_MODEL_ID", "llama3.2-vision")
    
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_ORG_ID: Optional[str] = os.getenv("OPENAI_ORG_ID")
    OPENAI_MODEL_ID: str = os.getenv("OPENAI_MODEL_ID", "gpt-4-turbo")

    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_DEPLOYMENT_NAME: Optional[str] = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")
    
    # Secret storage (mocked for now, implies OS keychain integration in real app)
    SECRETS = {
        "PASSWORD": "super_secret_password_123"
    }

    @staticmethod
    def get_secret(key: str) -> Optional[str]:
        return Config.SECRETS.get(key)
