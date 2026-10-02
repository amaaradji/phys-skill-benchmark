import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml
from dotenv import load_dotenv
from openai import OpenAI

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


def _user_env(name):
    value = os.environ.get(name)
    if value or sys.platform != "win32":
        return value
    # Windows user variables added after the parent process started are not inherited,
    # so read them from the registry rather than requiring an editor restart.
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            return winreg.QueryValueEx(key, name)[0]
        except FileNotFoundError:
            return None


def _openai_v1_url(endpoint):
    # Accepts either the OpenAI v1 URL or an Azure AI Foundry project URL.
    if "/openai/v1" in endpoint:
        return endpoint
    parsed = urlparse(endpoint)
    return f"{parsed.scheme}://{parsed.netloc}/openai/v1"


def load_config():
    with open(REPO_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def client_for(model_id):
    spec = load_config()["models"][model_id]
    names = {field: spec[field] for field in ("key_env", "endpoint_env", "deployment_env")}
    values = {field: _user_env(name) for field, name in names.items()}
    missing = [names[field] for field, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    client = OpenAI(base_url=_openai_v1_url(values["endpoint_env"]), api_key=values["key_env"])
    return client, values["deployment_env"]
