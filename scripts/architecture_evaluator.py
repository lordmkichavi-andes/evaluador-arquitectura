import difflib
import os
import requests
from flask import Flask, request, jsonify

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
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "top_p": 1.0,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0
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
        diff = list(difflib.unified_diff(before_lines, after_lines, fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""))
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

    def build_prompt(self, diagram_text, code_summary, features):
        return f"""
        Eres un asesor experimentado de arquitectura de software y respondes en español con un nivel de detalle, rigor técnico y perspectiva crítica sumamente altos. 
        Tu objetivo es evaluar la propuesta basándote en las Reglas Generales de Arquitectura que se te proporcionan, así como en los requerimientos (features) y los cambios de código (diff).
        Enfatiza tu análisis en aspectos técnicos y concretos relacionados con el Pull Request, el feature, el código modificado y el diagrama; evita respuestas excesivamente generales.

        El análisis debe ser exhaustivo y crítico, indicando de forma clara cómo se cumple o se viola cada regla pertinente, siempre que corresponda:
        - Menciona cualquier fortaleza o incumplimiento que detectes, vinculándolos directamente al PR, al feature, al código y al diagrama.
        - Justifica de manera técnica por qué ocurre esa observación (positiva o negativa).
        - Sugiere mejoras de arquitectura o diseño, de ser necesario.
        - Explica las consecuencias de no atender las reglas, contemplando ventajas y riesgos.
        - Concluye con una visión general de la calidad de la propuesta y tus conclusiones finales.

        **Reglas Generales de Arquitectura (para tu referencia):**
        {self.general_rules}

        **Requerimientos Específicos (Feature):**
        {features}

        **Diagrama (PlantUML):**
        {diagram_text}

        **Cambios Detectados (Diff):**
        {code_summary}
        """.strip()

    def evaluate(self, diagram_text, code_changes, features):
        summary = summarize_code_changes(code_changes, max_tokens=6000)
        prompt = self.build_prompt(diagram_text, summary, features)
        if approximate_token_count(prompt) > self.token_limit:
            words = prompt.split()
            prompt = " ".join(words[:self.token_limit])
        return azure_openai_inference(prompt, self.endpoint, self.api_key, self.deployment, max_tokens=self.token_limit)

app = Flask(__name__)

@app.route("/api/v1/architecture-eval", methods=["POST"])
def architecture_eval():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload received"}), 400
    email_info = data.get("email", {})
    developer_email = email_info.get("developer", "")
    leader_email = email_info.get("reviewer", "")
    diagram_text = data.get("diagram", "")
    code_changes = data.get("code", [])
    features = data.get("feature", "")
    evaluator = ArchitectureEvaluator()
    try:
        response = evaluator.evaluate(diagram_text, code_changes, features)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    response_data = {
        "leaderEmail": leader_email,
        "developerEmail": developer_email,
        "architectureAnalysis": response
    }
    return jsonify(response_data), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5013, use_reloader=False)
