TEMPLATE_1 = """Halo 同学你好 😊 可以先了解你的个人信息吗？

姓名：
电话号码：
学历：（例：SPM / UEC / IGCSE / A-Level / STPM / Diploma）
是否有想就读专业：
是否有想就读的院校：
总学费预算：（例：RM 30,000）
本地大学或海外留学：

请复制粘贴把个人信息写在：后面～谢谢"""

TEMPLATE_2 = """谢谢你提供的资料！📋

可以请你发一下成绩单吗？
📸 图片 或 📄 PDF 都可以～

请复制粘贴把信息写在：后面～谢谢"""

HUMAN_MODE_MSG = """我们的顾问会尽快联系你！😊

如有紧急问题，欢迎直接 WhatsApp 我们。"""

OVERSEAS_MSG = """感谢你的询问！🌏

海外留学咨询需要由我们专业顾问为你服务，我会马上通知我们的团队联系你～"""


def format_courses(courses: list[dict], pathway: str) -> str:
    if not courses:
        return "抱歉，暂时找不到符合条件的课程，我们的顾问会为你提供更多选择！"

    lines = [f"根据你的成绩，以下是为你推荐的课程 🎓\n（{pathway}）\n"]
    for i, c in enumerate(courses[:3], 1):
        fee = c.get("fee_local_total_myr", "")
        fee_str = f"RM {fee}" if fee else "请咨询"
        lines.append(
            f"{'─'*30}\n"
            f"*{i}. {c.get('course_name','')}"
            f"*\n🏫 {c.get('school_name','')}\n"
            f"⏱ {c.get('duration_display','')}\n"
            f"📅 入学：{c.get('intake_months_display','')}\n"
            f"💰 学费：{fee_str}"
        )

    lines.append(
        "\n{'─'*30}\n"
        "想了解更多详情或有其他问题，欢迎继续提问！😊"
    )
    return "\n".join(lines)
