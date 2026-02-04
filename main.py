import asyncio
import logging
import sys

print("Loading modules...", flush=True)
try:
    from semantic_kernel.contents.chat_history import ChatHistory
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
    from semantic_kernel.agents import ChatCompletionAgent
    print("Semantic Kernel modules loaded successfully.", flush=True)
except ImportError as e:
    print(f"Failed to load SK modules: {e}", flush=True)
    sys.exit(1)

from app.core.llm_factory import LLMFactory
from app.plugins.browser_plugin import BrowserPlugin
from app.plugins.perception_plugin import PerceptionPlugin

# Configure logging to see the agent's thought process
logging.basicConfig(level=logging.WARNING)

async def main():
    print("Initializing Probabilistic Browser Agent (Agent Logic)...", flush=True)
    
    # 1. Initialize Kernel with AI Service
    try:
        kernel = LLMFactory.create_kernel()
    except Exception as e:
        print(f"Error creating kernel (check config): {e}", flush=True)
        return
    
    # 2. Initialize Plugins
    browser = BrowserPlugin()
    perception = PerceptionPlugin(browser)
    
    # 3. Create the Agent
    # We define the agent with instructions on how to behave.
    # We enable auto function calling so it can use the plugins.
    
    agent = ChatCompletionAgent(
        kernel=kernel,
        name="BrowserAgent",
        instructions="""
        You are an autonomous browser agent. Your goal is to help the user achieve their task by interacting with the browser.
        
        You have two primary capabilities:
        1. Perception: You can 'observe' the screen to see what elements are available (IDs, names).
        2. Browser: You can navigate, click_element, and type_text.
        
        The standard loop is:
        1. If you don't know where you are or what's on screen, call PerceptionPlugin-observe.
        2. Based on the observation, decide the next action (click or type).
        3. If the goal is achieved, answer the user.
        
        Always check the observation before clicking! Use the numeric IDs provided in the observation.
        """,
        plugins=[browser, perception],
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
    )

    # 4. Execute User Goal
    user_goal = "Go to example.com and type my password into the login box."
    print(f"\nUser Goal: {user_goal}\n", flush=True)
    print("NOTE: Execution will effectively hang here if no LLM server (Ollama) is responding at localhost:11434", flush=True)

    chat_history = ChatHistory()
    chat_history.add_user_message(user_goal)
    
    try:
        # 5. Invoke the Agent
        async for response in agent.invoke(chat_history):
            if response.content:
                print(f"[Agent]: {response.content}", flush=True)
            
    except Exception as e:
        print(f"Error during execution: {e}", flush=True)
        # We expect a connection error if no server, but that proves imports work.
        if "Connection" in str(e) or "Failed to connect" in str(e) or "connect" in str(e).lower():
             print("\n[SUCCESS] SK imports worked, agent initialized, but failed to connect to LLM as expected.", flush=True)
        else:
             import traceback
             traceback.print_exc()

    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
