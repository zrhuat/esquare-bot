import base64, json, logging
import PIL.Image
import io
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.0-flash")

# ── Grade analysis ─────────────────────────────────────────────────────────────

GRADE_SYSTEM = """You are an expert at reading Malaysian exam results: SPM, UEC, IGCSE, A-Level, STPM.

Analyze the exam result image/document and output ONLY structured plain text with:
1. Exam Type: (SPM / UEC / IGCSE / A-Level / STPM / Other)
2. All subjects and grades (one per line, format: "Subject: Grade")
3. Total Credits: (for SPM: count Credit/A/B; for UEC: count Grade B and above)
4. Key Subjects (report grade and pass/fail status): BM, Sejarah/History, English, Maths
   Format each as: "SubjectName: Grade (pass/fail)" e.g. "BM: D (pass)" or "Sejarah: G (fail)"
5. Pathway Eligibility: list eligible levels (Certificate/Diploma/Foundation/Degree)

Be concise and accurate. Do not add commentary."""


def analyze_grade_image(image_bytes: bytes, mime: str = "image/jpeg") -> str:
    try:
        img = PIL.Image.open(io.BytesIO(image_bytes))
        resp = _model.generate_content([GRADE_SYSTEM, img, "Analyze this exam result slip."])
        return resp.text.strip()
    except Exception as e:
        logger.error("analyze_grade_image error: %s", e)
        return ""


def analyze_grade_pdf(pdf_bytes: bytes) -> str:
    try:
        b64 = base64.b64encode(pdf_bytes).decode()
        resp = _model.generate_content([
            GRADE_SYSTEM,
            {"mime_type": "application/pdf", "data": b64},
            "Analyze this exam result slip.",
        ])
        return resp.text.strip()
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
        resp = _model.generate_content(
            PROFILE_SYSTEM + "\n\nText: " + text,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
        return json.loads(resp.text.strip())
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
        resp = _model.generate_content(
            REG_SYSTEM + "\n\nText: " + text,
            generation_config=genai.GenerationConfig(response_mime_type="application/json"),
        )
        return json.loads(resp.text.strip())
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
        resp = _model.generate_content(
            CHAT_SYSTEM + f"\n\nStudent profile:\n{student_context}\n\nQuestion: {question}"
        )
        return resp.text.strip()
    except Exception as e:
        logger.error("answer_question error: %s", e)
        return "抱歉，暂时无法回答。请稍后再试或联系我们的顾问。"
