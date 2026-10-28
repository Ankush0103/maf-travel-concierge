"""
========================================================================================
File: multi_agent_workflow.py
Description:
    Interactive Multi-Agent Graph Workflow with Microsoft Agent Framework (MAF).
    Demonstrates multi-step dynamic routing and fan-in aggregation.

Execution Pipeline:
    1. PlannerAgent (Router) classifies intent as CULTURE or ADVENTURE.
    2. Edge condition safely unwraps the text payload and routes to the right specialist.
    3. Specialist (CultureAgent or AdventureAgent) creates targeted recommendations.
    4. BudgetAgent calculates costs, adds travel advice, and finalizes the output.
========================================================================================
"""

import sys
import time
import asyncio
import configparser
from pathlib import Path
from typing import Any

from agent_framework import Agent, WorkflowBuilder
from agent_framework.openai import OpenAIChatCompletionClient


# ======================================================================================
# STEP 1: Configuration Management (env.ini)
# ======================================================================================

def load_azure_config() -> dict[str, str]:
    """Loads and validates Azure connection settings from env.ini."""
    ini_path = Path(__file__).resolve().parent / "env.ini"
    if not ini_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {ini_path}")

    config = configparser.ConfigParser()
    config.read(ini_path)

    return {
        "endpoint": config.get("AZURE_OPENAI", "AZURE_ENDPOINT").strip(),
        "key": config.get("AZURE_OPENAI", "SUBSCRIPTION_KEY").strip(),
        "model": config.get("AZURE_OPENAI", "DEPLOYMENT_NAME", fallback="gpt-4o").strip(),
        "version": config.get("AZURE_OPENAI", "API_VERSION", fallback="2024-12-01-preview").strip(),
    }


# ======================================================================================
# STEP 2: Edge Condition Helper (Payload Unwrapper)
# ======================================================================================

def extract_agent_text(msg: Any) -> str:
    """
    Safely unwrap the actual response text from whatever payload the workflow passes.
    In MAF workflows, upstream agents pass an 'AgentExecutorResponse' where the model's
    generated text resides inside 'msg.agent_response.text'.
    """
    # Case 1: AgentExecutorResponse passed across workflow edges
    if hasattr(msg, "agent_response") and hasattr(msg.agent_response, "text"):
        return msg.agent_response.text or ""
    # Case 2: AgentResponse directly
    if hasattr(msg, "text"):
        return msg.text or ""
    # Case 3: Raw string fallback
    return str(msg)


# ======================================================================================
# STEP 3: Multi-Agent Workflow Factory
# ======================================================================================

def build_travel_workflow(client: OpenAIChatCompletionClient):
    """Assembles and compiles the multi-agent graph with all 3 stages."""
    
    # --- Agent 1: Router / Triage ---
    planner = Agent(
        client=client,
        name="PlannerAgent",
        instructions=(
            "You are a travel triage router. Analyze the user's travel request. "
            "If they ask about museums, history, classical art, cathedrals, or city architecture, "
            "output: 'CATEGORY: CULTURE' followed by a 1-sentence summary of what they want. "
            "If they ask about nature, hiking, mountain sports, outdoor thrills, or parks, "
            "output: 'CATEGORY: ADVENTURE' followed by a 1-sentence summary of what they want. "
            "Always include either the word CULTURE or ADVENTURE."
        ),
    )

    # --- Agent 2: Culture Specialist ---
    culture_agent = Agent(
        client=client,
        name="CultureAgent",
        instructions=(
            "You are a Cultural Travel Specialist. Based on the user's request and planner's note, "
            "recommend 3 specific world-class museums, historical landmarks, or art galleries. "
            "Keep each recommendation concise and highlight why it is special."
        ),
    )

    # --- Agent 3: Adventure Specialist ---
    adventure_agent = Agent(
        client=client,
        name="AdventureAgent",
        instructions=(
            "You are an Adventure and Outdoor Specialist. Based on the user's request and planner's note, "
            "recommend 3 scenic outdoor excursions, nature trails, or adventure activities. "
            "Keep each recommendation concise and exciting."
        ),
    )

    # --- Agent 4: Budget & Final Summary ---
    budget_agent = Agent(
        client=client,
        name="BudgetAgent",
        instructions=(
            "You are a Travel Budget and Logistics Advisor. "
            "Review the itinerary suggested by the specialist. "
            "Provide an estimated daily budget breakdown (Economy vs Moderate in USD/EUR), "
            "along with 1 practical travel tip (such as museum pass or transport cards). "
            "Present a finalized, well-formatted travel plan."
        ),
    )

    # Construct the graph
    builder = WorkflowBuilder(start_executor=planner)

    # Routing functions using the payload unwrapper
    def is_culture(msg: Any) -> bool:
        text = extract_agent_text(msg).lower()
        return "culture" in text

    def is_adventure(msg: Any) -> bool:
        text = extract_agent_text(msg).lower()
        return "adventure" in text

    # Add conditional edges from Planner
    builder.add_edge(planner, culture_agent, condition=is_culture)
    builder.add_edge(planner, adventure_agent, condition=is_adventure)

    # Add convergence edges: Whichever specialist ran routes into BudgetAgent
    builder.add_edge(culture_agent, budget_agent)
    builder.add_edge(adventure_agent, budget_agent)

    # Compile the workflow
    return builder.build()


# ======================================================================================
# STEP 4: Interactive Command-Line Interface
# ======================================================================================

async def main() -> None:
    try:
        cfg = load_azure_config()
    except Exception as e:
        print(f"[Configuration Error]: {e}")
        sys.exit(1)

    # Shared Azure OpenAI client
    client = OpenAIChatCompletionClient(
        model=cfg["model"],
        azure_endpoint=cfg["endpoint"],
        api_key=cfg["key"],
        api_version=cfg["version"],
    )

    print("\n[Compiling Multi-Agent Graph Workflow...]")
    workflow = build_travel_workflow(client)
    print("[Workflow Ready]")

    print("\n" + "=" * 70)
    print(" 🌍  Multi-Agent Travel Concierge (Type 'exit' or 'q' to quit)")
    print("=" * 70)

    while True:
        try:
            user_query = await asyncio.to_thread(input, "\nEnter your travel request: ")
            query_clean = user_query.strip()

            if not query_clean:
                continue

            if query_clean.lower() in ["exit", "quit", "q"]:
                print("\nSafe travels! Goodbye.")
                break

            print("\n⏳ Multi-Agent Execution Pipeline Running:")
            print("   Step 1: PlannerAgent categorizing...")
            print("   Step 2: Domain Specialist planning...")
            print("   Step 3: BudgetAgent finalizing...")

            start_time = time.time()
            result = await workflow.run(query_clean)
            duration = time.time() - start_time

            print("\n" + "=" * 70)
            print(f"📋 Multi-Agent Workflow Complete (Executed in {duration:.2f}s)")
            print("=" * 70)

            # Display each agent's contribution in order
            outputs = result.get_outputs()
            for i, out in enumerate(outputs):
                agent_name = getattr(out, "agent_id", None) or f"Stage {i + 1}"
                text_content = extract_agent_text(out)
                
                print(f"\n🔹 [{agent_name} Output]:")
                print("-" * 50)
                print(text_content)

        except (KeyboardInterrupt, EOFError):
            print("\n\nSession terminated by user.")
            break
        except Exception as ex:
            print(f"\n[Execution Error]: {ex}")


if __name__ == "__main__":
    asyncio.run(main())