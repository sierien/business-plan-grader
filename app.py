import os
import tempfile
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import fitz  # PyMuPDF
from docx import Document

app = Flask(__name__)

# Instantiate the OpenAI client
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ''
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def analyze_content(text, first_name, last_name, email):
    prompt = f"""
You are a business plan analyst. A user named {first_name} {last_name} ({email}) has submitted this content for review. Please analyze the following business plan and provide professional feedback on structure, clarity, and financial readiness.

Business Plan Content:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()

        file_url = data.get("file_url")
        file_type = data.get("file_type", "").lower()
        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        email = data.get("email", "")

        if not file_url or file_type not in ["pdf", "docx"]:
            return jsonify({"error": "Missing or invalid file_url or file_type"}), 400

        # Download the file
        response = requests.get(file_url)
        if response.status_code != 200:
            return jsonify({"error": "Failed to download file"}), 400

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name

        if file_type == "pdf":
            text = extract_text_from_pdf(tmp_path)
        elif file_type == "docx":
            text = extract_text_from_docx(tmp_path)
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        if not text.strip():
            return jsonify({"error": "The document appears to be empty"}), 400

        analysis = analyze_content(text, first_name, last_name, email)
        return jsonify({"analysis": analysis})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    return "Business Plan Grader is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
