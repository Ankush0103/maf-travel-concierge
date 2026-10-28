import configparser
from pathlib import Path
from openai import AzureOpenAI

ini_path = Path(__file__).resolve().parent / "env.ini"
config = configparser.ConfigParser()
config.read(ini_path)

client = AzureOpenAI(
    api_version=config.get("AZURE_OPENAI", "API_VERSION"),
    azure_endpoint=config.get("AZURE_OPENAI", "AZURE_ENDPOINT"),
    api_key=config.get("AZURE_OPENAI", "SUBSCRIPTION_KEY"),
)

response = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "I am going to Paris, what should I see?"},
    ],
    model=config.get("AZURE_OPENAI", "DEPLOYMENT_NAME"),
)

print(response.choices[0].message.content)