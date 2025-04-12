from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import uuid
import os
import openai
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
print("\napi_key working\n" if openai.api_key else "\napi_key not working\n")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow frontend access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

import openai

client = openai.OpenAI()  # Uses key from OPENAI_API_KEY env variable

async def summarize_text(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Summarize this exam page."},
                {"role": "user", "content": text}
            ],
            max_tokens=250,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print("❌ OpenAI Error:", e)
        return "שגיאה בסיכום הקובץ"


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    title = "לא הצלחנו לקרוא את שם המבחן"
    summary = "לא נוצר סיכום"

    if file.filename.lower().endswith(".pdf"):
        try:
            doc = fitz.open(file_path)
            first_page = doc.load_page(0)
            text = first_page.get_text().strip()
            if text:
                title = text.split('\n')[0]
                summary = await summarize_text(text)
        except Exception as e:
            print("PDF read error:", e)

    return JSONResponse(content={
        "filename": file.filename,
        "title": title,
        "summary": summary
    })
