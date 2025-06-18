from flask import Flask, request, jsonify
import requests
import os
import fitz  # PyMuPDF
import openai

app = Flask(__name__)

# Set your OpenAI API key (make sure it's defined in the Render dashboard)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/')
def index():
    return 'Business Plan Grader is running.'

@app.route('/analyze', methods=['POST'])
def analyze_plan():
    try:
        data = request.get_json()

        first_name = data.get("first_name", "N/A")
        last_name = data.get("last_name", "N/A")
        email = data.get("email", "N/A")
        coupon_code = data.get("coupon_code", "")
        consent = data.get("consent", "").lower() in ["true", "yes", "on"]
        file_url = data.get("file_url")

        if not consent:
            return jsonify({"error": "Consent not given"}), 400

        if not file_url:
            return jsonify({"error": "Missing file URL"}), 400

        # Try downloading the file
        try:
            response = requests.get(file_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"Failed to download file: {e}"}), 400

        # Save the file temporarily
        file_path = "/tmp/temp_file.pdf"
        with open(file_path, "wb") as f:
            f.write(response.content)

        # Extract text from PDF using PyMuPDF
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception as e:
            return jsonify({"error": f"Failed to read PDF: {e}"}), 500

        # Call OpenAI to analyze the text
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a business plan evaluator."},
                    {"role": "user", "content": f"Please evaluate the following business plan:\n\n{text[:10000]}"}
                ]
            )
            result = completion['choices'][0]['message']['content']
        except Exception as e:
            return jsonify({"error": f"OpenAI API error: {e}"}), 500

        return jsonify({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "evaluation": result
        })

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
