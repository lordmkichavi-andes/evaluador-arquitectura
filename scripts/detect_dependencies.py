import argparse
import re
import json
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff_file", required=True, help="Ruta al archivo .diff con las líneas + A -> B")
    args = parser.parse_args()

    output_dir = "build"
    output_file = os.path.join(output_dir, "detected_relations.json")

    os.makedirs(output_dir, exist_ok=True)

    with open(args.diff_file, "r", encoding="utf-8") as df:
        diff_text = df.read()

    pattern = re.compile(r'(\w+)\s*->\s*(\w+)')
    detected = []

    for line in diff_text.split('\n'):
        if line.startswith('+'):
            match = pattern.search(line)
            if match:
                left = match.group(1)
                right = match.group(2)
                detected.append([left, right])

    with open(output_file, "w", encoding="utf-8") as out:
        json.dump({"detected_relations": detected}, out, indent=2)

    print(f"Generado {output_file}, {len(detected)} relaciones detectadas.")

if __name__ == "__main__":
    main()
