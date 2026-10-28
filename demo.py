"""
========================================================================================
File: demo.py
Description:
    Demonstrates building and running an autonomous agent using the Microsoft 
    Agent Framework (MAF) integrated with Azure AI Foundry / Azure OpenAI Service.

What this file does:
    1. Loads Azure credentials (endpoint, API key, deployment name, API version)
       securely from a local 'env.ini' configuration file using Python's configparser.
    2. Initializes an 'OpenAIChatCompletionClient' configured for Azure OpenAI,
       which connects to the standard Chat Completions endpoint (/chat/completions).
    3. Defines a custom domain tool ('get_travel_recommendation') decorated with MAF's
       '@tool' decorator so the agent can discover and invoke it during reasoning.
    4. Instantiates an 'Agent' with a defined role, instructions, and tools.
    5. Dispatches an asynchronous user request, lets the model reason and call
       the registered tool, and prints the generated response.

Prerequisites:
    - Packages: agent-framework, agent-framework-openai
    - Configuration: env.ini in the same directory with [AZURE_OPENAI] section.
========================================================================================
"""

import asyncio
import configparser
from pathlib import Path
from typing import Annotated

# Core abstractions from the Microsoft Agent Framework
from agent_framework import Agent, tool

# Specialized client targeting the standard Chat Completions API (compatible with Azure)
from agent_framework.openai import OpenAIChatCompletionClient


# ======================================================================================
# STEP 1: Load and Validate Azure Configuration from env.ini
# ======================================================================================

# Locate 'env.ini' in the same folder as this script
ini_file_path = Path(__file__).resolve().parent / "env.ini"

if not ini_file_path.exists():
    raise FileNotFoundError(
        f"Missing configuration file: '{ini_file_path}'. "
        "Please ensure 'env.ini' exists with your Azure credentials."
    )

# Initialize configparser and read the file
config = configparser.ConfigParser()
config.read(ini_file_path)

# Extract Azure OpenAI connection parameters
azure_endpoint = config.get("AZURE_OPENAI", "AZURE_ENDPOINT").strip()
subscription_key = config.get("AZURE_OPENAI", "SUBSCRIPTION_KEY").strip()
deployment_name = config.get("AZURE_OPENAI", "DEPLOYMENT_NAME", fallback="gpt-4o").strip()
api_version = config.get("AZURE_OPENAI", "API_VERSION", fallback="2024-12-01-preview").strip()


# ======================================================================================
# STEP 2: Define Custom Agent Tools
# ======================================================================================

# The @tool decorator registers this Python function with Microsoft Agent Framework.
# The docstring and type annotations (Annotated) are translated into function-calling
# JSON schemas that the LLM uses to decide when and how to call the function.
@tool
def get_travel_recommendation(
    city: Annotated[str, "The name of the destination city (e.g., Paris, Tokyo)"]
) -> str:
    """Look up top recommended attractions, museums, and landmarks for a given city."""
    # Simulated knowledge base for demonstration purposes
    database = {
        "paris": (
            "Must-see spots in Paris: 1) The Eiffel Tower, 2) Louvre Museum, "
            "3) Notre-Dame Cathedral, 4) Montmartre & Sacré-Cœur, 5) Seine River Cruise."
        ),
        "tokyo": (
            "Must-see spots in Tokyo: 1) Senso-ji Temple, 2) Shibuya Sky & Crossing, "
            "3) Shinjuku Gyoen National Garden, 4) Meiji Shrine, 5) Akihabara district."
        ),
    }

    # Return city-specific data if found, or a fallback suggestion
    return database.get(
        city.lower().strip(),
        f"Explore the historical city center, local museums, and popular culinary markets in {city}."
    )


# ======================================================================================
# STEP 3: Configure Agent Client and Execute Task
# ======================================================================================

async def main() -> None:
    # Initialize the chat client targeting Azure OpenAI Chat Completions endpoint.
    # Note: OpenAIChatCompletionClient uses '/chat/completions', which avoids the
    # 400 'API version not supported' error caused by the Responses API endpoint.
    azure_chat_client = OpenAIChatCompletionClient(
        model=deployment_name,             # Deployed model name in Azure (e.g., 'gpt-4o')
        azure_endpoint=azure_endpoint,     # Endpoint (e.g., 'https://learnmaf.openai.azure.com/')
        api_key=subscription_key,         # Azure Subscription Key
        api_version=api_version,           # API version (e.g., '2024-12-01-preview')
    )

    # Instantiate the Agent with its persona, system instructions, and available tools
    agent = Agent(
        client=azure_chat_client,
        name="TravelAdvisorAgent",
        instructions=(
            "You are an expert travel advisor assistant. "
            "When the user asks about sightseeing or places to visit in a city, "
            "always invoke the 'get_travel_recommendation' tool to retrieve suggestions."
        ),
        tools=[get_travel_recommendation],
    )

    # Define the user query
    user_prompt = "I am going to Paris, what should I see?"
    print(f"User: {user_prompt}\n")

    # Execute the agent workflow asynchronously:
    # The agent submits the prompt -> model triggers tool call -> framework executes
    # 'get_travel_recommendation' -> model synthesizes the final response.
    response = await agent.run(user_prompt)

    # Display the final generated response
    print("Agent Response:")
    print(response.text)


# ======================================================================================
# Entrypoint
# ======================================================================================
if __name__ == "__main__":
    asyncio.run(main())