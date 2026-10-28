"""
========================================================================================
File: app.py
Description:
    Production FastAPI web application for deploying the Multi-Agent Travel
    Concierge on Azure App Service / Azure Container Apps.

Features:
    - Automatically reads from Azure Environment Variables (App Settings) in the cloud.
    - Gracefully falls back to local env.ini when tested on a local development machine.
    - Interactive Swagger API Documentation at /docs.
========================================================================================
"""

import os
import configparser
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent_framework.openai import OpenAIChatCompletionClient
from multi_agent_workflow import build_travel_workflow, extract_agent_text

app = FastAPI(
    title="Multi-Agent Travel Concierge API",
    description="Multi-agent travel planning service built with Microsoft Agent Framework and Azure OpenAI.",
    version="1.0.0",
)

def get_azure_credentials() -> dict[str, str]:
    """Retrieves credentials from Azure App Settings (Environment Variables) or local env.ini."""
    # Priority 1: Cloud Environment Variables (Azure App Service)
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    key = os.environ.get("AZURE_OPENAI_KEY") or os.environ.get("SUBSCRIPTION_KEY")
    model = os.environ.get("AZURE_OPENAI_MODEL") or os.environ.get("DEPLOYMENT_NAME", "gpt-4o")
    version = os.environ.get("AZURE_OPENAI_VERSION") or os.environ.get("API_VERSION", "2024-12-01-preview")

    # Priority 2: Local env.ini fallback
    if not (endpoint and key):
        ini_path = Path(__file__).resolve().parent / "env.ini"
        if ini_path.exists():
            cfg = configparser.ConfigParser()
            cfg.read(ini_path)
            endpoint = cfg.get("AZURE_OPENAI", "AZURE_ENDPOINT", fallback=endpoint)
            key = cfg.get("AZURE_OPENAI", "SUBSCRIPTION_KEY", fallback=key)
            model = cfg.get("AZURE_OPENAI", "DEPLOYMENT_NAME", fallback=model)
            version = cfg.get("AZURE_OPENAI", "API_VERSION", fallback=version)

    return {
        "endpoint": (endpoint or "").strip(),
        "key": (key or "").strip(),
        "model": (model or "gpt-4o").strip(),
        "version": (version or "2024-12-01-preview").strip(),
    }

# Lazy workflow initialization to prevent startup crashes when env vars are still being configured
_workflow = None

def get_workflow():
    global _workflow
    if _workflow is None:
        creds = get_azure_credentials()
        if not creds["endpoint"] or not creds["key"]:
            raise ValueError(
                "Azure OpenAI Endpoint or Subscription Key is missing. "
                "Please configure them in Azure App Settings or in a local 'env.ini' file."
            )
        client = OpenAIChatCompletionClient(
            model=creds["model"],
            azure_endpoint=creds["endpoint"],
            api_key=creds["key"],
            api_version=creds["version"],
        )
        _workflow = build_travel_workflow(client)
    return _workflow

class PlanRequest(BaseModel):
    query: str

class PlanResponse(BaseModel):
    query: str
    stages: list[dict[str, str]]
    final_plan: str

@app.get("/")
def root():
    return {"message": "Multi-Agent Travel Concierge API is live. Visit /docs for Swagger UI."}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/plan", response_model=PlanResponse)
async def generate_travel_plan(request: PlanRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    
    try:
        wf = get_workflow()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {e}")
    
    try:
        result = await wf.run(request.query)
        outputs = result.get_outputs()
        
        stages = []
        for i, out in enumerate(outputs):
            name = getattr(out, "agent_id", None) or f"Stage_{i + 1}"
            stages.append({
                "agent": name,
                "content": extract_agent_text(out)
            })
        
        final_plan = stages[-1]["content"] if stages else "No plan generated."
        return PlanResponse(query=request.query, stages=stages, final_plan=final_plan)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Execution error: {ex}")
