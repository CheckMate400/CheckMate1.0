from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import fitz  # PyMuPDF
import uuid
import os
import json
import openai
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
print("\napi_key working\n" if openai.api_key else "\napi_key not working\n")

# Initialize FastAPI app
app = FastAPI()

# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create base projects directory
PROJECTS_DIR = "projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)

client = openai.OpenAI()

# --------- Helpers ---------

def extract_text_from_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print("❌ PDF error:", e)
        return ""

# --------- Create Project Route ---------

@app.post("/create_project/")
async def create_project(
    project_name: str = Form(...),
    subject: str = Form(...),
    num_questions: int = Form(...),
    num_tests: int = Form(...),
    expected_average: Optional[int] = Form(None),
    solution_file: Optional[UploadFile] = File(None),
    test_files: List[UploadFile] = File(...)
):
    project_id = str(uuid.uuid4())
    project_path = os.path.join(PROJECTS_DIR, f"{project_name}_{project_id}")
    os.makedirs(project_path, exist_ok=True)
    tests_dir = os.path.join(project_path, "tests")
    os.makedirs(tests_dir, exist_ok=True)

    solution_text = ""
    if solution_file:
        solution_path = os.path.join(project_path, f"solution_{solution_file.filename}")
        with open(solution_path, "wb") as f:
            f.write(await solution_file.read())
        solution_text = extract_text_from_pdf(solution_path)

    # Extract test data
    student_texts = []
    for idx, test_file in enumerate(test_files):
        test_path = os.path.join(tests_dir, f"test_{idx+1}_{test_file.filename}")
        with open(test_path, "wb") as f:
            f.write(await test_file.read())
        student_texts.append((test_file.filename, extract_text_from_pdf(test_path)))

    # Create prompt
    grading_prompt = f"""
You are an intelligent and objective exam grader.

Subject: {subject}
Number of questions: {num_questions}

Reference solution:
{solution_text if solution_text else '[NO SOLUTION GIVEN — use your own knowledge]'}
The solution maybe incomplete, so use your own knowledge as well to grade the exam.

Grade the following student exams. Each answer should be graded from 0 to 100.
Adjust grading (if needed) so that the average score is approximately (10%) {expected_average if expected_average else 'natural'}.

Return for each student:
[{{
  "student": "filename",
  "grades": [{{ "question_number": int, "grade": int}}],
  "overall_score": grade
}}]
The comment part should explain the grading
Only output valid JSON.
"""

    student_blocks = "\n".join([
        f"STUDENT: {filename}\n{text}" for filename, text in student_texts
    ])

    full_prompt = grading_prompt + "\n\n" + student_blocks

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.0,
            max_tokens=4000
        )
        gpt_output = response.choices[0].message.content.strip()

        try:
            results = json.loads(gpt_output)
        except json.JSONDecodeError:
            print("❌ GPT returned invalid JSON:")
            print(gpt_output)
            return JSONResponse(status_code=500, content={"error": "Invalid GPT output."})

        return JSONResponse(content={
            "project_name": project_name,
            "num_tests": num_tests,
            "average": expected_average,
            "results": results
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
