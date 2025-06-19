import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
from docx import Document
import fitz  # PyMuPDF

# Initialize Flask app
app = Flask(__name__)

# Initialize OpenAI client using new v1+ SDK
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Common headers to mimic a browser
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document;q=0.9,*/*;q=0.8",
}

# Extract text from PDF
def extract_text_from_pdf(url):
    response = requests.get(url, headers=BROWSER_HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: status {response.status_code}")
    with open("temp.pdf", "wb") as f:
        f.write(response.content)
    doc = fitz.open("temp.pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Extract text from DOCX
def extract_text_from_docx(url):
    response = requests.get(url, headers=BROWSER_HEADERS)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: status {response.status_code}")
    with open("temp.docx", "wb") as f:
        f.write(response.content)
    doc = Document("temp.docx")
    return "\n".join([para.text for para in doc.paragraphs])

# Analyze text using OpenAI and return Zapier-friendly output
def analyze_text(text):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional business plan evaluator. "
                "Respond in this exact format:\n\n"
                "Grade: [letter]\n\n"
                "Summary: [1 short paragraph]\n\n"
                "Improvement Recommendations:\n"
                "1. [rec one]\n"
                "2. [rec two]\n"
                "3. [rec three]"
            )
        },
        {"role": "user", "content": text}
    ]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.4
    )

    raw = response.choices[0].message.content.strip()

    # Format with ||| for Zapier splitting
    try:
        parts = raw.split("Improvement Recommendations:")
        header = parts[0].strip()
        recs = parts[1].strip().split("\n")[:3]

        grade_line = header.split("\n\n")[0].replace("Grade:", "").strip()
        summary_line = header.split("\n\n")[1].replace("Summary:", "").strip()

        rec1 = recs[0].lstrip("1. ").strip()
        rec2 = recs[1].lstrip("2. ").strip()
        rec3 = recs[2].lstrip("3. ").strip()

        return f"{grade_line}|||{summary_line}|||{rec1}|||{rec2}|||{rec3}"

    except Exception:
        return raw  # Fallback if formatting fails

# Analyze endpoint
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

# Health check route
@app.route("/", methods=["GET"])
def home():
    return "Business Plan Grader API is live", 200

# Run the app
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
