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

def azure_openai_inference(prompt, endpoint, api_key, deployment, max_tokens=8000):
    body = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Eres un asesor experimentado de arquitectura de software "
                    "que responde en español de forma clara y completa. "
                    "Tu objetivo es analizar y explicar respetando las reglas que te den."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2
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

def summarize_code_changes(changes, max_tokens=6000):
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
            lines_out.append("... (Se ha alcanzado el límite de tokens en los encabezados) ...")
            break
        lines_out.append(header_line)
        total_tokens += header_tokens

        for dline in diff:
            line_tokens = approximate_token_count(dline)
            if total_tokens + line_tokens > max_tokens:
                lines_out.append("... (Se ha alcanzado el límite de tokens en el diff) ...")
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
        self.token_limit = int(os.environ.get("TOKEN_LIMIT", "8000"))
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
REGLAS GENERALES DE ARQUITECTURA:
{self.general_rules}

REQUERIMIENTOS ESPECÍFICOS:
{features}

DIAGRAMA (PlantUML):
{diagram_text}

CAMBIOS DETECTADOS:
{code_summary}

Instrucciones:
1. Determina si los cambios violan alguna regla o requerimiento.
2. Justifica tu respuesta (por qué o por qué no).
3. Sugiere mejoras concretas si las hay.
""".strip()

        print(f"\n[Prompt generado para Azure OpenAI]:\n{prompt}\n")
        return prompt

    def evaluate(self, diagram_text, code_changes, features):
        summary = summarize_code_changes(code_changes)
        prompt = self.build_prompt(diagram_text, summary, features)
        if approximate_token_count(prompt) > self.token_limit:
            print("[DEBUG] El prompt excede el token_limit, se recorta")
            words = prompt.split()
            prompt = " ".join(words[:self.token_limit])

        return azure_openai_inference(prompt, self.endpoint, self.api_key, self.deployment, max_tokens=self.token_limit)

    def extract_score(self, response):
        match = re.search(r"Score\s*=\s*([\d]+(\.\d+)?)", response)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return 0.0
        return 0.0
