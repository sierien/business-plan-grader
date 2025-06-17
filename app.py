from flask import Flask, request, jsonify
import openai
import os
import tempfile
from docx import Document
import fitz  # PyMuPDF

app = Flask(__name__)
openai.api_key = os.environ['OPENAI_API_KEY']

def extract_text(file_path, file_type):
    if file_type == 'application/pdf':
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text() for page in doc)
    elif file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

@app.route('/analyze', methods=['POST'])
def analyze():
    uploaded_file = request.files.get('file')
    email = request.form.get('email')
    first_name = request.form.get('first_name', '')
    last_name = request.form.get('last_name', '')
    name = f"{first_name} {last_name}".strip()

    if not uploaded_file:
        return jsonify({'error': 'No file uploaded'}), 400

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        uploaded_file.save(tmp.name)
        file_text = extract_text(tmp.name, uploaded_file.content_type)

    prompt = f"""
    Please review this business plan and provide:
    1. A letter grade (A, B, C, D, F) for lender-readiness.
    2. Identify any missing or underdeveloped sections.
    3. Provide 3–5 professional suggestions to improve clarity and lender appeal.

    Plan:
    {file_text[:15000]}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response['choices'][0]['message']['content']

    print(f"Review for {name} ({email}):\n{result}\n")

    return jsonify({"message": "Analysis complete", "summary": result})

if __name__ == '__main__':
    app.run(port=5000)
