from flask import Flask, request, jsonify
from architecture_evaluator import ArchitectureEvaluator
import sys

app = Flask(__name__)

@app.route("/api/v1/architecture-eval", methods=["POST"])
def architecture_eval():
    data = request.json
    if not data:
        print("[DEBUG] No JSON payload received", flush=True)
        return jsonify({"error": "No JSON payload received"}), 400

    email_info = data.get("email", {})
    developer_email = email_info.get("developer", "")
    leader_email = email_info.get("reviewer", "")
    diagram_text = data.get("diagram", "")
    code_changes = data.get("code", [])
    features = data.get("feature", "")

    print(f"[DEBUG] Received request:", flush=True)
    print(f"  Developer Email: {developer_email}", flush=True)
    print(f"  Leader Email: {leader_email}", flush=True)
    print(f"  Diagram Text: {diagram_text}", flush=True)
    print(f"  Features: {features}", flush=True)
    print(f"  Code Changes: {code_changes}", flush=True)

    evaluator = ArchitectureEvaluator()
    try:
        response = evaluator.evaluate(diagram_text, code_changes, features)
    except Exception as e:
        print(f"[ERROR] {str(e)}", flush=True)
        return jsonify({"error": str(e)}), 500

    score = evaluator.extract_score(response)
    print(f"[DEBUG] Response from evaluator: {response}", flush=True)
    print(f"[DEBUG] Extracted score: {score}", flush=True)

    response_data = {
        "leaderEmail": leader_email,
        "developerEmail": developer_email,
        "architectureAnalysis": response
    }

    return jsonify(response_data), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5013, use_reloader=False)
