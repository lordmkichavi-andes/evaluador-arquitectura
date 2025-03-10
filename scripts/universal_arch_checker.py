import argparse
import json
import re
import os
import requests

def hf_inference(prompt, model_name="distilgpt2", max_new_tokens=400, temperature=1.0, top_p=0.95):
    from transformers import AutoTokenizer, AutoModelForCausalLM
    device = "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)

    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=1024,
        temperature=temperature,
        top_p=top_p,
        do_sample=True
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

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
    data = r.json()
    return data["choices"][0]["message"]["content"]

def load_text_file(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""

def build_prompt(general_rules, requirements, xmi_arch, detected, token_limit):
    associations = xmi_arch.get("associations", [])
    interfaces = xmi_arch.get("interfaces", [])
    detected_rels = detected.get("detected_relations", [])

    def maybe_shorten(lst, max_len=20):
        if len(lst) > max_len:
            return lst[:max_len] + ["... (omitted) ..."]
        return lst

    short_asocs = maybe_shorten(associations)
    short_detected = maybe_shorten(detected_rels)

    prompt = f"""
Eres un asesor de arquitectura. 
Reglas Generales:
{general_rules}

Reglas / Requisitos Específicos:
{requirements}

Arquitectura (PlantUML / XMI):
Asociaciones: {short_asocs}
Interfaces: {interfaces}

Dependencias detectadas en PR:
{short_detected}

Comenta si viola las reglas y sugiere mejoras. 
Al final, escribe "Score=0.xx" (0=peor,1=mejor). 
No bloquees el PR, es solo recomendación.
"""
    if len(prompt) > token_limit:
        prompt = prompt[:token_limit] + "\n(Truncado por token_limit)\n"
    return prompt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="ArchitectureConfig.json")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as cf:
        config = json.load(cf)

    engine_type = config.get("engine_type", "huggingface")
    model_name = config.get("model_name", "distilgpt2")
    endpoint = config.get("openai_endpoint", "")
    api_key = config.get("openai_api_key", "")
    deployment = config.get("deployment_name", "")
    general_rules_file = config.get("general_rules_file", "rules/general_rules.md")
    requirements_file = config.get("requirements_file", "rules/requirements.md")
    xmi_arch_file = config.get("xmi_arch_file", "build/plantuml_arch.json")
    detected_file = config.get("detected_file", "build/detected_relations.json")
    behavior = config.get("behavior", "recommend_only")
    threshold = config.get("threshold", 0.7)
    token_limit = config.get("token_limit", 3000)

    general_rules = load_text_file(general_rules_file)
    requirements = load_text_file(requirements_file)

    with open(xmi_arch_file, "r", encoding="utf-8") as xf:
        xmi_arch = json.load(xf)
    with open(detected_file, "r", encoding="utf-8") as df:
        detected = json.load(df)

    prompt = build_prompt(general_rules, requirements, xmi_arch, detected, token_limit)
    print(prompt)
    print("----------------------------")

    if engine_type.lower() == "huggingface":
        response = hf_inference(prompt, model_name=model_name, max_new_tokens=400)
    elif engine_type.lower() == "azureopenai":
        response = azure_openai_inference(prompt, endpoint, api_key, deployment)
    else:
        print(f"[INFO] engine_type={engine_type} desconocido. Por defecto huggingface.")
        response = hf_inference(prompt, model_name=model_name, max_new_tokens=400)

    print("=== RESPUESTA IA ===")
    print(response, "\n")

    match = re.search(r"Score\s*=\s*([\d]+(\.\d+)?)", response)
    score = 0.5
    if match:
        score = float(match.group(1))
    print(f"Score detectado: {score}")

    if behavior == "recommend_only":
        print("No se bloqueará el PR, es solo recomendación.")
    else:
        if score < threshold:
            print(f"Score < {threshold} => se podría bloquear.")
        else:
            print("Score >= threshold => OK para integrar.")

if __name__ == "__main__":
    main()
