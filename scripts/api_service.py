from flask import Flask, request, jsonify

from architecture_evaluator import ArchitectureEvaluator

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
    evaluator = ArchitectureEvaluator()
    try:
        response = evaluator.evaluate(diagram_text, code_changes)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    score = evaluator.extract_score(response)
    response_data = {
        "leaderEmail": leader_email,
        "developerEmail": developer_email,
        "architectureAnalysis": response
    }
    return jsonify(response_data), 200

if __name__ == "__main__":
    app.run(debug=True, port=5013)
