import os
import requests
import fitz  # PyMuPDF
import docx
from flask import Flask, request, jsonify
from io import BytesIO
import openai

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_file(file_url):
    response = requests.get(file_url)
    if response.status_code != 200:
        raise ValueError("Failed to download file")

    content_type = response.headers.get("Content-Type", "")
    if "pdf" in content_type:
        with fitz.open(stream=response.content, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    elif "wordprocessingml" in content_type or file_url.lower().endswith(".docx"):
        doc = docx.Document(BytesIO(response.content))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type")

def generate_analysis(text, first_name, last_name, email):
    prompt = f"""
You are a professional business plan evaluator. Analyze the following business plan and provide:
1. An executive summary evaluation.
2. Strengths and weaknesses.
3. Suggestions to improve the plan's viability for lenders or investors.
4. Any red flags or missing components.
Limit the response to 500 words.

Business Plan submitted by {first_name} {last_name} ({email}):

{text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    return response.choices[0].message["content"]

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.json
        file_url = data.get("file_url")
        if not file_url:
            return jsonify({"error": "file_url is required"}), 400

        first_name = data.get("first_name", "")
        last_name = data.get("last_name", "")
        email = data.get("email", "")
        coupon = data.get("coupon_code", "")
        consent = data.get("consent", "").lower() == "true"

        if not consent:
            return jsonify({"error": "User did not give consent"}), 403

        text = extract_text_from_file(file_url)
        analysis = generate_analysis(text, first_name, last_name, email)

        return jsonify({"analysis": analysis})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
