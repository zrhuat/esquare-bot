import logging, os, re, requests as http
from flask import Flask, request, jsonify
import sheets, ai
from rules import (
    is_greeting_only, is_registration_form,
    needs_human, determine_eligible_levels, map_interest_to_subfield,
)
from templates import TEMPLATE_1, TEMPLATE_2, HUMAN_MODE_MSG, OVERSEAS_MSG, format_courses
from config import TELEGRAM_TOKEN, STAFF_CHAT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
TG_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}"

COURSE_RE = re.compile(r"推荐|课程|学校|读什么|什么课|哪个学校|suitable|recommend", re.I)


def send(chat_id, text):
    try:
        http.post(f"{TG_API}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        logger.error("send error: %s", e)


def download_file(file_id):
    info = http.get(f"{TG_API}/getFile", params={"file_id": file_id}, timeout=10).json()
    path = info["result"]["file_path"]
    return http.get(f"{TG_FILE}/{path}", timeout=30).content


def handle_grade_media(message):
    if "photo" in message:
        data = download_file(message["photo"][-1]["file_id"])
        return ai.analyze_grade_image(data, "image/jpeg")
    if "document" in message:
        doc = message["document"]
        mime = doc.get("mime_type", "")
        data = download_file(doc["file_id"])
        if mime == "application/pdf" or doc.get("file_name", "").lower().endswith(".pdf"):
            return ai.analyze_grade_pdf(data)
        if mime.startswith("image/"):
            return ai.analyze_grade_image(data, mime)
    return ""


def notify_staff(student, reason):
    if not STAFF_CHAT_ID:
        return
    send(STAFF_CHAT_ID,
         f"*需要人工跟进*\n原因: {reason}\n"
         f"姓名: {student.get('姓名','?')}\n"
         f"电话: {student.get('电话号码','-')}\n"
         f"Chat ID: {student.get('chat_id','-')}")


def send_recommendation(chat_id, student):
    grade_text = student.get("成绩单", "")
    interest = student.get("想就读专业", "")
    eligible_levels, pathway_summary = determine_eligible_levels(grade_text)
    tab, allowed_sub = map_interest_to_subfield(interest)
    courses = sheets.query_courses(allowed_sub, eligible_levels, tab)
    if not courses and not allowed_sub:
        send(chat_id,
             "根据你的成绩，你符合：*" + pathway_summary + "*\n\n"
             "请问你有兴趣读哪个方向？\n"
             "💼 商科（会计/市场营销）\n"
             "💻 IT（电脑科学/软件工程）\n"
             "🏥 医疗（护理/药剂）\n"
             "⚙️ 工程\n"
             "🎨 设计\n"
             "📖 其他")
        return
    if not courses:
        courses = sheets.query_courses([], eligible_levels, tab)
    send(chat_id, format_courses(courses, pathway_summary))


def handle_message(message):
    chat_id = str(message.get("chat", {}).get("id", ""))
    if not chat_id:
        return

    text = (message.get("text") or message.get("caption") or "").strip()
    has_media = "photo" in message or "document" in message

    student = sheets.get_student(chat_id)
    has_profile = bool(student.get("姓名"))
    has_grades = bool(student.get("成绩单"))

    # Human mode
    if student.get("need_human") == "YES":
        send(chat_id, HUMAN_MODE_MSG)
        return

    # Registration form
    if text and is_registration_form(text):
        reg_data = ai.extract_registration(text)
        sheets.save_registration(chat_id, reg_data)
        sheets.update_student(chat_id, {"source_text": text[:500]})
        send(chat_id, "✅ 报名资料已收到！我们的顾问会尽快联系你。")
        notify_staff({**student, "chat_id": chat_id}, "收到报名表格")
        return

    # Overseas / APEL
    if text and needs_human(text) and not has_profile:
        sheets.set_human_mode(chat_id, True)
        send(chat_id, OVERSEAS_MSG)
        notify_staff({**student, "chat_id": chat_id}, f"海外询问：{text[:80]}")
        return

    # Grade image or PDF
    if has_media:
        send(chat_id, "⏳ 正在识别成绩单，请稍等...")
        analysis = handle_grade_media(message)
        if analysis:
            sheets.update_student(chat_id, {"成绩单": analysis})
            student["成绩单"] = analysis
            has_grades = True
            send(chat_id, f"✅ 成绩识别完成！\n\n{analysis}")
            if has_profile:
                send_recommendation(chat_id, student)
            else:
                send(chat_id, TEMPLATE_1)
        else:
            send(chat_id, "抱歉，无法识别该文件。请发送清晰的图片或 PDF 📄")
        return

    if not text:
        return

    # Greeting or very short message
    if is_greeting_only(text) or (not has_profile and not has_grades and len(text) < 8):
        send(chat_id, TEMPLATE_1)
        return

    # Try AI profile extraction from any text
    profile_data = ai.extract_profile(text)
    profile_data = {k: v for k, v in profile_data.items() if v and str(v).strip()}

    if profile_data.get("姓名") or profile_data.get("电话号码"):
        sheets.update_student(chat_id, {**profile_data, "source_text": text[:500]})
        student.update(profile_data)
        has_profile = bool(student.get("姓名"))
        if has_profile and has_grades:
            send(chat_id, "✅ 资料已更新！")
            send_recommendation(chat_id, student)
        elif has_profile:
            send(chat_id, TEMPLATE_2)
        else:
            send(chat_id, TEMPLATE_1)
        return

    # Route by state
    if not has_profile:
        send(chat_id, TEMPLATE_1)
        return
    if not has_grades:
        send(chat_id, TEMPLATE_2)
        return

    # Has profile + grades: answer or recommend
    context = (f"姓名:{student.get('姓名')} 学历:{student.get('学历')} "
               f"专业:{student.get('想就读专业')} 成绩:{student.get('成绩单','')[:150]}")
    if COURSE_RE.search(text):
        send_recommendation(chat_id, student)
    else:
        send(chat_id, ai.answer_question(context, text))


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    msg = data.get("message") or data.get("edited_message")
    if msg:
        try:
            handle_message(msg)
        except Exception as e:
            logger.exception("error: %s", e)
    return {"ok": True}


@app.route("/health")
def health():
    return "OK"


@app.route("/set_webhook")
def set_webhook_route():
    from config import WEBHOOK_URL
    r = http.get(f"{TG_API}/setWebhook", params={"url": f"{WEBHOOK_URL}/webhook"})
    return r.json()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
