import asyncio
import os
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from app.core.llm_factory import LLMFactory
from app.config import Config
from semantic_kernel.contents.chat_history import ChatHistory

# Force Azure provider for testing, or rely on .env
# os.environ["LLM_PROVIDER"] = "azure" 

async def test_azure_connection():
    print("Testing Azure OpenAI Connection...", flush=True)
    
    # Ensure config is set (you must have set these in your environment or .env file)
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("ERROR: AZURE_OPENAI_ENDPOINT not set in environment.")
        print("Please set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME.")
        return

    try:
        # Create kernel using the factory logic
        kernel = LLMFactory.create_kernel()
        
        # Create a simple chat history
        history = ChatHistory()
        history.add_user_message("Hello, Azure! Are you working?")
        
        # Get the chat completion service
        service_id = "default_chat"
        chat_service = kernel.get_service(service_id)
        
        # Invoke
        print("Sending request to Azure...", flush=True)
        # Create execution settings
        settings = AzureChatPromptExecutionSettings(service_id=service_id)

        response = await chat_service.get_chat_message_content(
            chat_history=history,
            settings=settings 
        )
        
        print(f"\n[SUCCESS] Azure Response: {response.content}", flush=True)

    except Exception as e:
        print(f"\n[FAILURE] Error connecting to Azure: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(test_azure_connection())
