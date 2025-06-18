from flask import Flask, request, jsonify
from openai import OpenAI
import os
import tempfile
import requests
from docx import Document
import fitz  # PyMuPDF

app = Flask(__name__)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def extract_text(file_path, content_type):
    if content_type == 'application/pdf' or file_path.lower().endswith('.pdf'):
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text() for page in doc)
    elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or file_path.lower().endswith('.docx'):
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("🔥 Incoming JSON POST to /analyze")
        data = request.get_json(force=True)
        print("🔥 Incoming JSON:", data)

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        coupon_code = data.get('coupon_code', '')
        consent = data.get('consent', 'off')
        file_url = data.get('file_url', '')

        full_name = f"{first_name} {last_name}".strip()
        print(f"✅ Parsed: {full_name}, email: {email}, file_url: {file_url}")

        if str(consent).lower() not in ['on', 'yes', 'true', '1']:
            print("❌ Consent not given")
            return jsonify({"error": "Consent not given"}), 400

        if not file_url or not file_url.startswith("http"):
            print("❌ Invalid or missing file_url")
            return jsonify({"error": "Invalid or missing file_url"}), 400

        try:
            response = requests.get(file_url)
            response.raise_for_status()
        except Exception as e:
            print("❌ File download failed:", str(e))
            return jsonify({"error": "Failed to download file"}), 400

        content_type = response.headers.get('Content-Type', '')
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            tmp.write(response.content)
            tmp.flush()
            file_text = extract_text(tmp.name, content_type)

        if not file_text.strip():
            print("❌ No extractable text in uploaded file")
            return jsonify({"error": "Unable to extract text from uploaded file"}), 400

        prompt = f"""
        Please review this business plan and provide:
        1. A letter grade (A, B, C, D, F) for lender-readiness.
        2. Identify any missing or underdeveloped sections important for SBA or commercial funding (e.g., DSCR, CapEx, repayment, competitive positioning).
        3. Offer 3–5 professional-level improvement suggestions to strengthen clarity, credibility, or completeness.

        Business plan text:
        {file_text[:15000]}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert business plan reviewer."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response.choices[0].message.content
        print(f"🎯 AI Review Complete for {full_name}")

        return jsonify({
            "message": "Analysis complete",
            "summary": result,
            "name": full_name,
            "email": email,
            "coupon_code": coupon_code
        })

    except Exception as e:
        print("❌ Unexpected server error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
