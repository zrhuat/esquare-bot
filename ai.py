"""
OpenAI API calls.
- analyze_grade_image: GPT-4o vision → structured grade text
- extract_profile: GPT-4o-mini → structured profile dict
- extract_registration: GPT-4o-mini → registration dict
"""
import base64, json, logging, re
from openai import OpenAI
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Grade analysis ─────────────────────────────────────────────────────────────

GRADE_SYSTEM = """You are an expert at reading Malaysian exam results: SPM, UEC, IGCSE, A-Level, STPM.

Analyze the exam result image/document and output ONLY structured plain text with:
1. Exam Type: (SPM / UEC / IGCSE / A-Level / STPM / Other)
2. All subjects and grades (one per line, format: "Subject: Grade")
3. Total Credits: (for SPM: count Credit/A/B; for UEC: count Grade B and above)
4. Key Subjects: BM (pass/credit/fail), English (pass/credit/fail), Maths (pass/credit/fail)
5. Pathway Eligibility: list eligible levels (Certificate/Diploma/Foundation/Degree)

Be concise and accurate. Do not add commentary."""


def analyze_grade_image(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    b64 = base64.b64encode(image_bytes).decode()
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": GRADE_SYSTEM},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}},
                    {"type": "text", "text": "Analyze this exam result slip."},
                ]},
            ],
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("analyze_grade_image error: %s", e)
        return ""


def analyze_grade_pdf(pdf_bytes: bytes) -> str:
    """Convert first page of PDF to image, then analyze."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2, 2)  # 2x zoom for clarity
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("jpeg")
        doc.close()
        return analyze_grade_image(img_bytes, "image/jpeg")
    except Exception as e:
        logger.error("analyze_grade_pdf error: %s", e)
        return ""


# ── Profile extraction ─────────────────────────────────────────────────────────

PROFILE_SYSTEM = """Extract student profile fields from the text below.
Output ONLY valid JSON with these exact keys (use empty string "" if not found):
{
  "姓名": "",
  "电话号码": "",
  "学历": "",
  "想就读专业": "",
  "想就读院校": "",
  "总学费预算": "",
  "本地或海外": ""
}

Rules:
- 姓名: full name
- 电话号码: Malaysian phone number (01xxxxxxx)
- 学历: SPM / UEC / IGCSE / A-Level / STPM / Diploma / etc.
- 想就读专业: intended field/course (e.g. Accounting, Nursing, IT)
- 想就读院校: preferred university/college (e.g. Sunway, UCSI, Taylor's)
- 总学费预算: budget (preserve original text, e.g. RM 30,000)
- 本地或海外: 本地 or 海外
Output JSON only, no markdown, no explanation."""


def extract_profile(text: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROFILE_SYSTEM},
                {"role": "user", "content": text},
            ],
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        logger.error("extract_profile error: %s", e)
        return {}


# ── Registration form extraction ───────────────────────────────────────────────

REG_SYSTEM = """Extract registration form data from the text.
Output ONLY valid JSON with these exact keys (empty string if not found):
{
  "Name": "",
  "IC_Number": "",
  "Address": "",
  "Phone": "",
  "Religion": "",
  "Email": "",
  "Age_Form": "",
  "High_School": "",
  "Program_Interested": "",
  "Intake": "",
  "Parent_Name": "",
  "Occupation": "",
  "Income_Level": "",
  "Parent_Phone": "",
  "Parent_IC": "",
  "Parent_Email": ""
}
Output JSON only."""


def extract_registration(text: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": REG_SYSTEM},
                {"role": "user", "content": text},
            ],
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content.strip())
    except Exception as e:
        logger.error("extract_registration error: %s", e)
        return {}


# ── General question answer ────────────────────────────────────────────────────

CHAT_SYSTEM = """You are ESquare's friendly Malaysian education counselor chatbot.
You help students choose university courses in Malaysia.
Reply in the same language the student uses (Chinese/English/Malay).
Be concise, warm, and helpful. Max 3 sentences unless explaining course details."""


def answer_question(student_context: str, question: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CHAT_SYSTEM},
                {"role": "user", "content": f"Student profile:\n{student_context}\n\nQuestion: {question}"},
            ],
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("answer_question error: %s", e)
        return "抱歉，暂时无法回答。请稍后再试或联系我们的顾问。"
