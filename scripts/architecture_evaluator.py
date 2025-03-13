import re
import requests
import json
import os

def load_text_file(path):
    if os.path.exists(path):
        return open(path, "r", encoding="utf-8").read()
    return ""

def azure_openai_inference(prompt, endpoint, api_key, deployment, max_tokens=800):
    body = {
        "messages": [
            {"role": "system", "content": "Eres un software architecture assistant en español."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0
    }
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
    r = requests.post(url, headers=headers, json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def summarize_code_changes(changes, max_files=5):
    lines = []
    for i, c in enumerate(changes):
        if i >= max_files:
            lines.append("... (Hay más archivos modificados) ...")
            break
        path = c.get("path", "")
        added = c["after"].count("\n") + 1 if c.get("after") else 0
        removed = c["before"].count("\n") + 1 if c.get("before") else 0
        lines.append(f"{path}: +{added}, -{removed}")
    return "\n".join(lines)

class ArchitectureEvaluator:
    def __init__(self, config_path=None):
        if not config_path:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(script_dir, "..", "ArchitectureConfig.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.general_rules = load_text_file(
            os.path.join(script_dir, "..", self.config.get("general_rules_file", "rules/general_rules.md")))
        self.requirements = load_text_file(
            os.path.join(script_dir, "..", self.config.get("requirements_file", "rules/requirements.md")))
        self.endpoint = self.config.get("openai_endpoint", "")
        self.api_key = self.config.get("openai_api_key", "")
        self.deployment = self.config.get("deployment_name", "")
        self.token_limit = self.config.get("token_limit", 3000)

    def build_prompt(self, diagram_text, code_summary):
        return f"""
Eres un asesor de arquitectura. 
Reglas Generales:
{self.general_rules}
Reglas / Requisitos Específicos:
{self.requirements}
Diagrama (PlantUML):
{diagram_text}
Cambios detectados:
{code_summary}
Comenta si viola las reglas y sugiere mejoras. 
Al final, escribe "Score=0.xx" (0=peor,1=mejor). 
No bloquees el PR, es solo recomendación.
""".strip()
    def evaluate(self, diagram_text, code_changes):
        summary = summarize_code_changes(code_changes)
        prompt = self.build_prompt(diagram_text, summary)
        if len(prompt) > self.token_limit:
            prompt = prompt[:self.token_limit]
        return azure_openai_inference(prompt, self.endpoint, self.api_key, self.deployment)
    def extract_score(self, response):
        match = re.search(r"Score\s*=\s*([\d]+(\.\d+)?)", response)
        if match:
            try:
                return float(match.group(1))
            except:
                return 0.0
        return 0.0
