from flask import Flask, request, jsonify
import openai
import os
import requests
from docx import Document
import fitz  # PyMuPDF
import tempfile

app = Flask(__name__)

openai.api_key = os.environ.get('OPENAI_API_KEY')

def extract_text_from_file(file_url, file_type):
    response = requests.get(file_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: {response.status_code}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    if file_type == "docx":
        doc = Document(tmp_path)
        return "\n".join([p.text for p in doc.paragraphs])
    elif file_type == "pdf":
        with fitz.open(tmp_path) as pdf:
            return "\n".join([page.get_text() for page in pdf])
    else:
        raise ValueError("Unsupported file type")

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        file_type = data.get('file_type')
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        coupon_code = data.get('coupon_code')
        consent = data.get('consent')

        if not all([file_url, file_type, email, first_name, last_name, consent]):
            return jsonify({"error": "Missing required fields"}), 400

        if str(consent).lower() not in ["true", "yes", "on", "1"]:
            return jsonify({"error": "Consent not given"}), 400

        text = extract_text_from_file(file_url, file_type)

        prompt = f"""You are an expert in business plans. Review the following content and provide:
1. A grade (A+ to F) based on clarity, strategy, financial realism, and lender/investor appeal.
2. A short summary of strengths and weaknesses.
3. Suggestions to improve it.

Business Plan Text:
{text}
"""

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert business plan reviewer."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content
        return jsonify({"result": result})
    except Exception as e:
        import traceback
        print("❌ Unexpected error:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return 'Business Plan Grader is live.', 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
