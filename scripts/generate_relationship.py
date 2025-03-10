import re
import json
import os

def parse_plantuml(plantuml_file):
    class_pattern = re.compile(r'^\s*(class|interface)\s+(\w+)')
    rel_pattern = re.compile(r'^\s*(\w+)\s+([\.\-\*o]+(?:>\??)?)\s+(\w+)')
    classes = []
    associations = []
    with open(plantuml_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            c_match = class_pattern.match(line)
            if c_match:
                _, name = c_match.groups()
                classes.append(name)
                continue
            r_match = rel_pattern.match(line)
            if r_match:
                left, arrow, right = r_match.groups()
                associations.append([left, right, arrow])
    return classes, associations

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plantuml_file")
    parser.add_argument("--output", default="build/plantuml_arch.json")
    args = parser.parse_args()

    os.makedirs("build", exist_ok=True)
    classes, associations = parse_plantuml(args.plantuml_file)
    data = {
        "classes": classes,
        "associations": associations
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Archivo JSON generado en {args.output}")

if __name__ == "__main__":
    main()
