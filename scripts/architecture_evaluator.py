import re
import requests
import json
import os
import difflib

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

def summarize_code_changes(
    changes,
    max_char_length=2000,
    max_files=10,
    max_lines_per_file=50
):
    lines_out = []
    total_char_count = 0
    displayed_files = 0

    for i, change in enumerate(changes):
        if displayed_files >= max_files:
            lines_out.append(f"... (Existen {len(changes) - i} archivos adicionales) ...")
            break

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

        file_header = f"\n--- Resumen de cambios en: {path} ---"
        if total_char_count + len(file_header) > max_char_length:
            lines_out.append("... (Se ha alcanzado el límite de caracteres) ...")
            break
        lines_out.append(file_header)
        total_char_count += len(file_header)

        if len(diff) > max_lines_per_file:
            truncated_diff = diff[:max_lines_per_file]
            truncated_diff.append(
                f"... (Se han omitido {len(diff) - max_lines_per_file} líneas) ..."
            )
        else:
            truncated_diff = diff

        for dline in truncated_diff:
            if total_char_count + len(dline) + 1 > max_char_length:
                lines_out.append("... (Se ha alcanzado el límite de caracteres) ...")
                break
            lines_out.append(dline)
            total_char_count += len(dline) + 1

        displayed_files += 1
        if total_char_count >= max_char_length:
            break

    summary = "\n".join(lines_out)
    return summary.strip()

class ArchitectureEvaluator:
    def __init__(self, config_path=None):
        if not config_path:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(script_dir, "..", "ArchitectureConfig.json")

        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.general_rules = load_text_file(
            os.path.join(script_dir, "..", self.config.get("general_rules_file", "rules/general_rules.md"))
        )

        self.endpoint = self.config.get("openai_endpoint", "")
        self.api_key = self.config.get("openai_api_key", "")
        self.deployment = self.config.get("deployment_name", "")
        self.token_limit = self.config.get("token_limit", 3000)

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

        return prompt

    def evaluate(self, diagram_text, code_changes, features):
        summary = summarize_code_changes(code_changes)

        prompt = self.build_prompt(diagram_text, summary, features)

        print("------")
        print(prompt)

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
