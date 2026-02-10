from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, AzureChatCompletion
import openai
# Note: Semantic Kernel's Ollama support might be via OpenAI compatible interface or specific connector depending on version.
# For this implementation, we will use the OpenAI connector pointing to Ollama as it is a common pattern for "local-first" compatibility.

from app.config import Config

class LLMFactory:
    @staticmethod
    def create_kernel() -> Kernel:
        kernel = Kernel()

        service_id = "default_chat"

        if Config.LLM_PROVIDER == "ollama":
            # Ollama provides an OpenAI compatible API
            # Since SK OpenAIChatCompletion doesn't accept base_url directly in this version,
            # we inject a configured AsyncOpenAI client.
            
            client = openai.AsyncOpenAI(
                base_url=Config.OLLAMA_BASE_URL,
                api_key="ollama", # Arbitrary key for local
            )
            
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id=service_id,
                    ai_model_id=Config.OLLAMA_MODEL_ID,
                    async_client=client
                )
            )
            print(f"Kernel initialized with Ollama ({Config.OLLAMA_MODEL_ID}) via AsyncOpenAI")

        elif Config.LLM_PROVIDER == "openai":
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required for openai provider")
            
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id=service_id,
                    ai_model_id=Config.OPENAI_MODEL_ID,
                    api_key=Config.OPENAI_API_KEY,
                    org_id=Config.OPENAI_ORG_ID
                )
            )
            print(f"Kernel initialized with OpenAI ({Config.OPENAI_MODEL_ID})")

        elif Config.LLM_PROVIDER == "azure":
            if not Config.AZURE_OPENAI_ENDPOINT or not Config.AZURE_OPENAI_API_KEY or not Config.AZURE_OPENAI_DEPLOYMENT_NAME:
                raise ValueError("AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME are required for azure provider")
            
            kernel.add_service(
                AzureChatCompletion(
                    service_id=service_id,
                    deployment_name=Config.AZURE_OPENAI_DEPLOYMENT_NAME,
                    endpoint=Config.AZURE_OPENAI_ENDPOINT,
                    api_key=Config.AZURE_OPENAI_API_KEY,
                    api_version=Config.AZURE_OPENAI_API_VERSION
                )
            )
            print(f"Kernel initialized with Azure OpenAI ({Config.AZURE_OPENAI_DEPLOYMENT_NAME})")
        
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {Config.LLM_PROVIDER}")

        return kernel
