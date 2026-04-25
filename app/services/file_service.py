import io
import pandas as pd
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY

_MODEL = "models/gemini-2.5-flash"

_EXTRACT_PROMPT = (
    "You are a business data analyst. "
    "Read the document below and extract all key information: "
    "metrics, figures, trends, risks, and any data relevant to business decision-making. "
    "Output concise, structured bullet points. Do not add commentary or filler text."
)


def _client() -> genai.Client:
    return genai.Client(api_key=GEMINI_API_KEY)


def process_pdf(file_bytes: bytes, filename: str) -> str:
    client = _client()
    uploaded = client.files.upload(
        file=io.BytesIO(file_bytes),
        config=types.UploadFileConfig(
            mime_type="application/pdf",
            display_name=filename,
        ),
    )
    response = client.models.generate_content(
        model=_MODEL,
        contents=[_EXTRACT_PROMPT, uploaded],
    )
    return response.text


def process_csv(file_bytes: bytes) -> str:
    client = _client()
    df = pd.read_csv(io.BytesIO(file_bytes))
    preview = df.head(200).to_csv(index=False)
    shape_note = f"(Dataset: {len(df)} rows × {len(df.columns)} columns)\n\n"
    prompt = f"{_EXTRACT_PROMPT}\n\n{shape_note}CSV data:\n{preview}"
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
    )
    return response.text


def process_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    if "pdf" in content_type or filename.lower().endswith(".pdf"):
        return process_pdf(file_bytes, filename)
    if "csv" in content_type or filename.lower().endswith(".csv"):
        return process_csv(file_bytes)
    raise ValueError(f"Unsupported file type: {content_type}")
