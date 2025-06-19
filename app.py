import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from docx import Document
import fitz  # PyMuPDF

# Initialize Flask app
app = Flask(__name__)

# Initialize OpenAI client (v1+ SDK)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_text_from_pdf(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: status {response.status_code}")
    with open("temp.pdf", "wb") as f:
        f.write(response.content)
    doc = fitz.open("temp.pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(url):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: status {response.status_code}")
    with open("temp.docx", "wb") as f:
        f.write(response.content)
    doc = Document("temp.docx")
    return "\n".join([para.text for para in doc.paragraphs])

def analyze_text(text):
    messages = [
        {"role": "system", "content": "You are a professional business plan evaluator. Provide the following as plain text:\n1. Grade (A–F)\n2. Summary paragraph\n3. Three numbered improvement recommendations. Use double newlines to separate each section."},
        {"role": "user", "content": text}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # use 3.5 for token efficiency
        messages=messages,
        temperature=0.4
    )

    result = response.choices[0].message.content.strip()

    # Use ||| as a separator for Zapier-friendly formatting
    return result.replace("\n\n", "|||")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    file_url = data.get("file_url")
    file_type = data.get("file_type", "").lower()

    if not file_url or file_type not in ["pdf", "docx"]:
        return jsonify({"error": "Missing or invalid file_url or file_type"}), 400

    try:
        if file_type == "pdf":
            text = extract_text_from_pdf(file_url)
        else:
            text = extract_text_from_docx(file_url)

        result = analyze_text(text)

        return jsonify({
            "status": "success",
            "grade_result": result
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    return "Business Plan Grader API is live", 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
