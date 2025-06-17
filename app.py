from flask import Flask, request, jsonify
import openai
import os
import tempfile
from docx import Document
import fitz  # PyMuPDF

app = Flask(__name__)
openai.api_key = os.environ.get('OPENAI_API_KEY')


def extract_text(file_path, file_type):
    if file_type == 'application/pdf':
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text() for page in doc)
    elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""


@app.route('/analyze', methods=['GET', 'HEAD', 'POST'])
def analyze():
    if request.method in ['GET', 'HEAD']:
        # Allow Forminator's webhook test to succeed
        return '', 200

    try:
        print("🔥 Incoming POST to /analyze")
        print("Form keys:", list(request.form.keys()))
        print("File keys:", list(request.files.keys()))

        # Match Forminator field slugs
        first_name = request.form.get('text-2', '')
        last_name = request.form.get('text-3', '')
        email = request.form.get('email-1', 'N/A')
        coupon_code = request.form.get('text-1', '')
        consent = request.form.get('consent-1', 'off')
        uploaded_file = request.files.get('upload-1')

        full_name = f"{first_name} {last_name}".strip()

        print(f"✅ Parsed: {full_name}, email: {email}, consent: {consent}, coupon: {coupon_code}")

        if consent != 'on':
            return jsonify({"error": "Consent not given"}), 400

        if not uploaded_file:
            return jsonify({"error": "No file uploaded"}), 400

        # Save uploaded file and extract text
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            uploaded_file.save(tmp.name)
            file_text = extract_text(tmp.name, uploaded_file.content_type)

        if not file_text.strip():
            return jsonify({"error": "File content could not be extracted"}), 400

        # AI prompt for business plan grading
        prompt = f"""
        Please review this business plan and provide:
        1. A letter grade (A, B, C, D, F) for lender-readiness.
        2. Identify any missing or underdeveloped sections important for SBA or commercial funding.
        3. Provide 3–5 professional-level suggestions to improve the plan’s clarity, credibility, or effectiveness.

        Business plan text:
        {file_text[:15000]}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert business plan reviewer."},
                {"role": "user", "content": prompt}
            ]
        )

        result = response['choices'][0]['message']['content']

        print(f"\n=== Business Plan Review for {full_name} ({email}) ===")
        print(f"Coupon Code: {coupon_code}")
        print(result)
        print("\n===========================\n")

        return jsonify({"message": "Analysis complete", "summary": result})

    except Exception as e:
        print("❌ Exception:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
