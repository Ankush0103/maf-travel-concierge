# Multi-Agent Travel Concierge (Microsoft Agent Framework)

A production-grade, graph-based multi-agent application built with **Microsoft Agent Framework (MAF)** and **Azure OpenAI Service (Azure AI Foundry)**.

---

## Architecture Overview

```
                      ┌──────────────────────┐
                      │     User Query       │
                      └──────────┬───────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │    PlannerAgent      │
                      │  (Triage / Router)   │
                      └──────────┬───────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           │ [condition: 'culture']                    │ [condition: 'adventure']
           ▼                                           ▼
 ┌──────────────────────┐                    ┌──────────────────────┐
 │    CultureAgent      │                    │    AdventureAgent    │
 │ (Museums & History)  │                    │ (Outdoor & Thrills)  │
 └─────────┬────────────┘                    └──────────┬───────────┘
           │                                            │
           └─────────────────────┬──────────────────────┘
                                 │
                                 ▼
                      ┌──────────────────────┐
                      │     BudgetAgent      │
                      │(Estimates Daily Cost)│
                      └──────────┬───────────┘
                                 │
                                 ▼
                      Final Itinerary & Plan
```

### Agents
1. **`PlannerAgent` (Router)**: Evaluates user intent and dynamically classifies it as `CULTURE` or `ADVENTURE`.
2. **`CultureAgent`**: Suggests world-class museums, historical architecture, and cultural highlights.
3. **`AdventureAgent`**: Suggests outdoor trails, parks, viewpoints, and scenic excursions.
4. **`BudgetAgent` (Synthesizer)**: Calculates daily budget estimates (Economy vs Moderate) and practical tips.

---

## Project Structure

```text
MAF/
├── .gitignore              # Protects secrets from being committed to GitHub
├── env.ini                 # Local ONLY - Contains real Azure OpenAI keys (Do NOT commit)
├── env.ini.example         # Template for required environment variables
├── requirements.txt        # Python package dependencies
├── multi_agent_workflow.py # Core Microsoft Agent Framework Multi-Agent Graph
├── app.py                  # FastAPI Production Web API for Azure Web App / Container App
├── demo.py                 # Single-agent interactive CLI demo
├── demo_azure.py           # Direct Azure OpenAI SDK connection test
└── README.md               # Documentation and deployment commands
```

---

## 1. Local Setup and Execution

### Step 1: Create and Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Local Credentials
Copy `env.ini.example` to `env.ini` and fill in your Azure OpenAI subscription key:
```ini
[AZURE_OPENAI]
AZURE_ENDPOINT = https://l....maf.ope...i.azure.com/
SUBSCRIPTION_KEY = <your-actual-azure-key>
DEPLOYMENT_NAME = gpt-4o
API_VERSION = 2024-12-01-preview
```

### Step 4: Run Multi-Agent Interactive CLI
```powershell
python multi_agent_workflow.py
```

### Step 5: Run as Local FastAPI Web Server
```powershell
uvicorn app:app --reload --port 8000
```
Open interactive Swagger UI at: **`http://127.0.0.1:8000/docs`**

---

## 2. Deploy to Azure via Azure CLI

### Step 1: Push Code to GitHub
Ensure `env.ini` is in `.gitignore` so your private API key is never pushed:
```powershell
git init
git add .
git commit -m "Initial commit: Multi-Agent Travel Concierge"
git branch -M main
git remote set-url origin https://github.com/<your-username>/maf-travel-concierge.git
git push -u origin main
```

### Step 2: Create Azure App Service and Deploy
Run the following commands in Azure CLI:

```powershell
# 1. Log in to Azure
az login

# 2. Set variables
$RG       = "rg-maf-agents"
$LOCATION = "eastus"
$PLAN     = "plan-maf-linux"
$APP      = "maf-concierge-app" # Pick a globally unique name
$REPO     = "https://github.com/<your-username>/maf-travel-concierge"

# 3. Create Resource Group and Linux Plan
az group create --name $RG --location $LOCATION
az appservice plan create --name $PLAN --resource-group $RG --is-linux --sku B1

# 4. Create Web App with Python 3.12
az webapp create --name $APP --resource-group $RG --plan $PLAN --runtime "PYTHON:3.12"

# 5. Configure Secrets in Azure App Settings (Securely injected at runtime)
az webapp config appsettings set --resource-group $RG --name $APP --settings `
    AZURE_OPENAI_ENDPOINT="https://le...f.op....i.azure.com/" `
    AZURE_OPENAI_KEY="<your-actual-azure-key>" `
    AZURE_OPENAI_MODEL="gpt-4o" `
    AZURE_OPENAI_VERSION="2024-12-01-preview" `
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"

# 6. Set Startup Command for FastAPI
az webapp config set --resource-group $RG --name $APP --startup-file "python -m uvicorn app:app --host 0.0.0.0 --port 8000"

# 7. Pull and Deploy from GitHub
az webapp deployment source config --name $APP --resource-group $RG --repo-url $REPO --branch main --manual-integration
```

Your live API will be available at: **`https://<APP>.azurewebsites.net/docs`**
