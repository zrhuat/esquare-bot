import re

TEMPLATE_1 = """Halo 同学你好 😊 可以先了解你的个人信息吗？

姓名：
电话号码：
学历（SPM/UEC）：
是否有想就读专业：
是否有想就读的院校：
总学费预算：
本地大学 / 海外留学：
方便分享成绩给我们吗（图片/ PDF）

请复制粘贴把个人信息写在：后面～谢谢"""

TEMPLATE_2 = """谢谢你提供的资料！📋

可以请你发一下成绩单吗？
📸 图片 或 📄 PDF 都可以～

把以上资料填在图片说明（caption）里一起发过来也可以 😊"""

HUMAN_MODE_MSG = """我们的顾问会尽快联系你！😊

如有紧急问题，欢迎直接 WhatsApp 我们。"""

OVERSEAS_MSG = """感谢你的询问！🌏

海外留学咨询需要由我们专业顾问为你服务，我会马上通知我们的团队联系你～"""

PATHWAY_QUESTION = """根据你的成绩，你可以选择两条路线：

1️⃣ *Foundation*（约1年，直升 Degree 第一年）
2️⃣ *Diploma*（约2.5年，可 credits transfer 升入 Degree 第二年）

回复 *1* 选 Foundation，回复 *2* 选 Diploma 😊"""

DIRECTION_GUIDE = """了解！还没有确定方向没关系，让我帮你理清一下 😊

请问你平时比较喜欢或擅长哪些科目？
📐 理科（数学/物理/化学/生物）
📝 文科（语言/历史/地理）
🎨 艺术与设计
💼 商科（会计/经济）
💻 电脑与科技

你对哪类工作比较有兴趣？
👩‍⚕️ 帮助别人（医疗/教育/辅导）
💻 技术研究（编程/工程/数据）
🎨 创意设计（设计/媒体/艺术）
💼 商业管理（市场/会计/管理）
⚙️ 动手操作（工程/机械）"""

REGISTRATION_FORM = """太好了！请帮我填写以下报名表格，我们的顾问会尽快跟进 😊

Name:
IC number:
Address:
Hp number:
Religion:
Email:
Form/Age:
High school name:
Program interested:
Intake:
Parent name:
Occupation:
Householdincome:
B40/M40/T20
Parent contact number:
Parent NRIC:
Parent Email:

请复制粘贴把信息写在：后面～谢谢"""


def _parse_scholarship(scholarship_details: str, a_count: int) -> str:
    if not scholarship_details or a_count <= 0:
        return ""
    best_n, best_amt = 0, ""
    for m in re.finditer(r"(\d+)\s*[Aa][+=:\-]\s*(RM\s*[\d,]+|[\d,]+)", scholarship_details):
        n = int(m.group(1))
        amt = m.group(2).strip()
        if not amt.upper().startswith("RM"):
            amt = "RM " + amt
        if n <= a_count and n >= best_n:
            best_n, best_amt = n, amt
    if best_amt:
        return best_amt
    if scholarship_details and len(scholarship_details) < 150:
        return scholarship_details
    return "有奖学金（请咨询详情）"


def format_courses(courses: list, pathway: str, a_count: int = 0) -> str:
    if not courses:
        return "抱歉，暂时找不到符合条件的课程，我们的顾问会为你提供更多选择！"

    lines = [f"根据你的成绩，以下是为你推荐的课程 🎓\n（{pathway}）\n"]
    for i, c in enumerate(courses[:3], 1):
        fee = c.get("fee_local_total_myr", "")
        fee_str = f"RM {fee}" if fee else "请咨询"

        scholarship_line = ""
        if c.get("has_scholarship") and a_count > 0:
            amt = _parse_scholarship(str(c.get("scholarship_details", "")), a_count)
            if amt:
                scholarship_line = f"\n🎁 奖学金：{amt}（你有 {a_count}A）"

        lines.append(
            "─" * 28 + "\n"
            f"*{i}. {c.get('course_name', '')}*\n"
            f"🏫 {c.get('school_name', '')}\n"
            f"⏱ {c.get('duration_display', '')}\n"
            f"📅 入学：{c.get('intake_months_display', '')}\n"
            f"💰 学费：{fee_str}"
            f"{scholarship_line}"
        )

    lines.append(
        "\n" + "─" * 28 + "\n"
        "想了解更多详情，欢迎继续提问！😊\n"
        "如果确定了学校，告诉我你想 *报名*，我帮你准备表格～"
    )
    return "\n".join(lines)
