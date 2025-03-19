import os
import re
import requests
import difflib

def load_text_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
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

def approximate_token_count(text):
    return len(text.split())

def summarize_code_changes(changes, max_tokens=3000):
    lines_out = []
    total_tokens = 0

    for change in changes:
        path = change.get("path", "unknown_file")
        before_lines = change.get("before", "").splitlines()
        after_lines = change.get("after", "").splitlines()
        diff = list(difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        ))
        if not diff:
            continue
        header_line = f"\n--- Resumen de cambios en: {path} ---"
        header_tokens = approximate_token_count(header_line)
        if total_tokens + header_tokens > max_tokens:
            lines_out.append("... (Se ha alcanzado el límite de tokens) ...")
            break
        lines_out.append(header_line)
        total_tokens += header_tokens

        for dline in diff:
            line_tokens = approximate_token_count(dline)
            if total_tokens + line_tokens > max_tokens:
                lines_out.append("... (Se ha alcanzado el límite de tokens) ...")
                break
            lines_out.append(dline)
            total_tokens += line_tokens

        if total_tokens >= max_tokens:
            break
    return "\n".join(lines_out).strip()

class ArchitectureEvaluator:
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        self.token_limit = int(os.environ.get("TOKEN_LIMIT", "3000"))
        rules_file = os.environ.get("GENERAL_RULES_FILE", "rules/general_rules.md")
        self.general_rules = load_text_file(rules_file)

        print(f"\n[Configuration Loaded]")
        print(f"AZURE_OPENAI_ENDPOINT: {self.endpoint}")
        print(f"AZURE_OPENAI_API_KEY: {'***' if self.api_key else '(no key)'}")
        print(f"AZURE_OPENAI_DEPLOYMENT: {self.deployment}")
        print(f"TOKEN_LIMIT: {self.token_limit}")
        print(f"GENERAL_RULES_FILE: {rules_file}")
        print(f"GENERAL_RULES Loaded?: {'Yes' if self.general_rules else 'No'}\n")

    def build_prompt(self, diagram_text, code_summary, features):
        prompt = f"""
Eres un asesor de arquitectura.

========================================
 Reglas Generales de Arquitectura
========================================
{self.general_rules}

========================================
 Requerimientos Específicos (features)
========================================
{features}

========================================
 Diagrama (PlantUML)
========================================
{diagram_text}

========================================
 Cambios detectados
========================================
{code_summary}

Comenta si viola las reglas y sugiere mejoras.
Al final, escribe "Score=0.xx" (0=peor, 1=mejor).
No bloquees el PR, es solo recomendación.
""".strip()
        print(f"\n[Prompt generado para Azure OpenAI]:\n{prompt}\n")
        return prompt

    def evaluate(self, diagram_text, code_changes, features):
        summary = summarize_code_changes(code_changes)
        prompt = self.build_prompt(diagram_text, summary, features)
        if len(prompt) > self.token_limit:
            prompt = prompt[:self.token_limit]
        return azure_openai_inference(prompt, self.endpoint, self.api_key, self.deployment)

    def extract_score(self, response):
        match = re.search(r"Score\s*=\s*([\d]+(\.\d+)?)", response)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0.0
        return 0.0
