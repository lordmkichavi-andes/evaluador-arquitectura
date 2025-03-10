from transformers import AutoTokenizer, AutoModelForCausalLM

def generar_texto(
    model_name: str,
    prompt: str,
    max_length: int = 100,
    temperature: float = 1.0,
    top_p: float = 0.95,
    do_sample: bool = True,
    device: str = "cpu"
) -> str:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)

    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    outputs = model.generate(
        **inputs,
        max_length=max_length,
        temperature=temperature,
        top_p=top_p,
        do_sample=do_sample
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

if __name__ == "__main__":
    modelo = "distilgpt2"
    prompt_ejemplo = "Write a short poem about Artificial Intelligence:"
    texto_generado = generar_texto(
        model_name=modelo,
        prompt=prompt_ejemplo,
        max_length=100,
        temperature=1.0,
        top_p=0.95,
        do_sample=True,
        device="cpu"
    )
    print(texto_generado)
