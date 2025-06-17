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
    else:
        return ""

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        uploaded_file = request.files.get('file')
        email = request.form.get('email', 'N/A')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip()

        if not uploaded_file:
            return jsonify({"error": "No file uploaded"}), 400

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            uploaded_file.save(tmp.name)
            file_text = extract_text(tmp.name, uploaded_file.content_type)

        if not file_text.strip():
            return jsonify({"error": "File content could not be extracted"}), 400

        prompt = f"""
        Please review this business plan and provide:
        1. A letter grade (A, B, C, D, F) for lender-readiness.
        2. Identify any missing or underdeveloped sections that are important for funding (e.g., DSCR, CapEx, repayment, competitive analysis).
        3. Provide 3–5 professional-level improvement suggestions to strengthen clarity, credibility, or effectiveness.

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
        print(f"\n=== Analysis for {full_name} ({email}) ===\n{result}\n")

        return jsonify({"message": "Analysis complete", "summary": result})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
