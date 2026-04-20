"""
Pure deterministic rules — zero AI.
SPM/UEC pathway + sub_field mapping.
"""
import re

# ── Greeting detection ────────────────────────────────────────────────────────
GREETINGS = re.compile(
    r"^\s*(hi|hello|halo|hey|你好|哈囉|嗨|你好啊|早上好|晚上好|下午好"
    r"|good morning|good afternoon|good evening|test|testing|start|开始)\s*[!！.。]*\s*$",
    re.I,
)


def is_greeting_only(text: str) -> bool:
    return bool(GREETINGS.match(text.strip()))


# ── Registration form detection ───────────────────────────────────────────────
REG_KEYWORDS = [
    r"IC[_\s]?[Nn]umber\s*:",
    r"IC\s*:",
    r"Address\s*:",
    r"Religion\s*:",
    r"Occupation\s*:",
    r"Income[_\s]?Level\s*:",
    r"Parent[_\s]?Name\s*:",
    r"Parent[_\s]?Phone\s*:",
]


def is_registration_form(text: str) -> bool:
    hits = sum(1 for p in REG_KEYWORDS if re.search(p, text, re.I))
    return hits >= 3


# ── Profile info detection ────────────────────────────────────────────────────
PROFILE_PATTERNS = [
    re.compile(r"姓名[：:]"),
    re.compile(r"电话[：:]"),
    re.compile(r"学历[：:]"),
    re.compile(r"是否有想就读"),
    re.compile(r"总学费预算"),
    re.compile(r"本地大学|海外留学"),
    re.compile(r"name\s*:", re.I),
    re.compile(r"hp\s*(number)?\s*:", re.I),
    re.compile(r"phone\s*:", re.I),
]


def has_profile_data(text: str) -> bool:
    return sum(1 for p in PROFILE_PATTERNS if p.search(text)) >= 2


# ── Overseas / APEL detection ─────────────────────────────────────────────────
OVERSEAS_RE = re.compile(
    r"overseas|abroad|海外|出国|australia|united kingdom|uk\b|us\b|usa|canada"
    r"|singapore|new zealand|ireland|英国|澳洲|美国|加拿大|新加坡|纽西兰",
    re.I,
)
APEL_RE = re.compile(r"\bapel\b|成人|工作经验|working experience", re.I)


def needs_human(text: str) -> bool:
    return bool(OVERSEAS_RE.search(text) or APEL_RE.search(text))


# ── SPM grade parsing ─────────────────────────────────────────────────────────
def _spm_credits(text: str) -> int:
    m = re.search(r"total credits?\s*[：:]\s*(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    return len(re.findall(r"\(CREDIT\)", text, re.I))


def _spm_has(text: str, subject_pattern: str) -> bool:
    return bool(re.search(subject_pattern + r".*\(CREDIT\)|\(CREDIT\).*" + subject_pattern, text, re.I))


def _spm_pathway(text: str) -> tuple[list[str], str]:
    credits = _spm_credits(text)
    has_bm = _spm_has(text, r"Bahasa Melayu|BM")
    has_sej = _spm_has(text, r"Sejarah")
    has_math = _spm_has(text, r"Math|Matematik")
    has_eng = _spm_has(text, r"English|Bahasa Inggeris|BI")

    levels = []
    if credits >= 1:
        levels.append("CERTIFICATE")
    if credits >= 3 and has_bm and has_sej:
        levels.append("DIPLOMA")
    if credits >= 5 and has_bm and has_sej:
        levels.append("FOUNDATION")
    # SPM → Degree is NEVER allowed directly
    summary = (
        f"SPM | {credits} credits"
        + (" | BM✓" if has_bm else "")
        + (" | Sejarah✓" if has_sej else "")
        + (" | Maths✓" if has_math else "")
        + (" | English✓" if has_eng else "")
        + f" | Eligible: {', '.join(levels) or 'CERTIFICATE only'}"
    )
    return levels, summary


def _uec_pathway(text: str) -> tuple[list[str], str]:
    m = re.search(r"grade\s*b[^:：]*[：:]\s*(\d+)", text, re.I)
    b_count = int(m.group(1)) if m else len(re.findall(r"\b[AB][1-6]\b", text))

    if b_count >= 5:
        levels = ["DEGREE"]
        label = "DEGREE only (UEC 5+ Grade B)"
    elif b_count >= 3:
        levels = ["FOUNDATION", "DIPLOMA"]
        label = "FOUNDATION or DIPLOMA (UEC 3-4 Grade B)"
    else:
        levels = ["CERTIFICATE", "DIPLOMA"]
        label = "CERTIFICATE / DIPLOMA (UEC 1-2 Grade B)"

    summary = f"UEC | {b_count} Grade B | Eligible: {label}"
    return levels, summary


def _igcse_pathway(text: str) -> tuple[list[str], str]:
    credits = len(re.findall(r"grade\s*[ABC]", text, re.I))
    levels = []
    if credits >= 3:
        levels = ["FOUNDATION", "DIPLOMA"]
    elif credits >= 1:
        levels = ["CERTIFICATE", "DIPLOMA"]
    summary = f"IGCSE | ~{credits} credits | Eligible: {', '.join(levels) or 'CERTIFICATE'}"
    return levels, summary


def determine_eligible_levels(grade_text: str) -> tuple[list[str], str]:
    """Returns (eligible_level_list, human_readable_summary)"""
    t = grade_text.upper()
    if "UEC" in t or "统考" in t:
        return _uec_pathway(grade_text)
    if "IGCSE" in t or "O LEVEL" in t or "O-LEVEL" in t:
        return _igcse_pathway(grade_text)
    if "A LEVEL" in t or "A-LEVEL" in t or "STPM" in t:
        return ["DEGREE", "FOUNDATION"], f"A-Level/STPM | Eligible: DEGREE, FOUNDATION"
    if "SPM" in t:
        return _spm_pathway(grade_text)
    # Unknown — allow all
    return ["CERTIFICATE", "DIPLOMA", "FOUNDATION", "DEGREE"], "Unknown exam | All levels shown"


# ── Sub_field mapping ─────────────────────────────────────────────────────────
_SUB_MAP = [
    # FINANCE
    (r"\baccounting\b|会计",            "FINANCE", ["ACCOUNTING", "ACCOUNTING_FINANCE"]),
    (r"actuarial|精算",                  "FINANCE", ["ACTUARIAL_SCIENCE"]),
    (r"\bbanking\b|银行",                "FINANCE", ["BANKING"]),
    (r"\bfinance\b|理财",                "FINANCE", ["FINANCE", "ACCOUNTING_FINANCE"]),
    # BUSINESS
    (r"\bmarketing\b|市场营销|营销",     "BUSINESS", ["MARKETING"]),
    (r"human.?resource|\bhr\b|人力资源", "BUSINESS", ["HUMAN_RESOURCE"]),
    (r"\bbusiness\b|\bmanagement\b|商业|管理|commerce", "BUSINESS",
     ["BUSINESS_MANAGEMENT", "MANAGEMENT", "BUSINESS_ADMINISTRATION"]),
    # ENGINEERING
    (r"civil.?eng|土木工程",             "ENGINEERING", ["CIVIL_ENGINEERING"]),
    (r"mechanical.?eng|机械工程",        "ENGINEERING", ["MECHANICAL_ENGINEERING"]),
    (r"electrical.?eng|electronic|电子|电气", "ENGINEERING",
     ["ELECTRICAL_ENGINEERING", "ELECTRONIC_ENGINEERING"]),
    (r"chemical.?eng|化学工程",          "ENGINEERING", ["CHEMICAL_ENGINEERING"]),
    (r"mechatronics|robotics|机电",      "ENGINEERING", ["MECHATRONICS", "ROBOTICS"]),
    (r"\bengineering\b|工程",            "ENGINEERING",
     ["CIVIL_ENGINEERING", "MECHANICAL_ENGINEERING", "ELECTRICAL_ENGINEERING",
      "CHEMICAL_ENGINEERING", "MECHATRONICS"]),
    # IT
    (r"computer.?science|\bcs\b|计算机", "IT", ["COMPUTER_SCIENCE"]),
    (r"software.?eng|软件工程",          "IT", ["SOFTWARE_ENGINEERING"]),
    (r"cybersecurity|network.?security|网络安全", "IT", ["CYBERSECURITY", "NETWORK_SECURITY"]),
    (r"data.?science|data.?analytics|数据科学", "IT",
     ["DATA_SCIENCE", "DATA_ANALYTICS", "COMPUTER_SCIENCE"]),
    (r"artificial.?intelligence|\bai\b|machine.?learning|人工智能", "IT",
     ["ARTIFICIAL_INTELLIGENCE", "DATA_SCIENCE", "COMPUTER_SCIENCE"]),
    (r"game.?dev|游戏",                  "IT", ["GAME_DEVELOPMENT", "COMPUTER_SCIENCE"]),
    (r"\bit\b|information.?tech|电脑|编程|programming", "IT",
     ["COMPUTER_SCIENCE", "INFORMATION_TECHNOLOGY", "SOFTWARE_ENGINEERING"]),
    # MEDICAL
    (r"\bnursing\b|护理",                "MEDICAL", ["NURSING"]),
    (r"\bmedicine\b|\bmbbs\b|医学|medical.?degree", "MEDICAL", ["MEDICINE", "MBBS"]),
    (r"pharmacy|药剂",                   "MEDICAL", ["PHARMACY"]),
    (r"physiotherapy|物理治疗",          "MEDICAL", ["PHYSIOTHERAPY"]),
    (r"dentistry|牙医",                  "MEDICAL", ["DENTISTRY"]),
    (r"biomedical|生物医学",             "MEDICAL", ["BIOMEDICAL", "BIOMEDICAL_SCIENCE"]),
    (r"\bmedical\b|医",                  "MEDICAL",
     ["NURSING", "MEDICINE", "PHARMACY", "PHYSIOTHERAPY", "BIOMEDICAL"]),
    # DESIGN
    (r"graphic.?design|平面设计",        "DESIGN", ["GRAPHIC_DESIGN"]),
    (r"interior.?design|室内设计",       "DESIGN", ["INTERIOR_DESIGN"]),
    (r"fashion|时装",                    "DESIGN", ["FASHION_DESIGN"]),
    (r"animation|动画",                  "DESIGN", ["ANIMATION", "DIGITAL_MEDIA"]),
    (r"\bdesign\b|设计",                 "DESIGN",
     ["GRAPHIC_DESIGN", "INTERIOR_DESIGN", "ANIMATION", "FASHION_DESIGN"]),
    # MEDIA
    (r"\bfilm\b|电影|vfx",               "MEDIA", ["FILM_VFX", "FILM"]),
    (r"mass.?comm|journalism|传媒|新闻", "MEDIA", ["MASS_COMMUNICATION", "JOURNALISM"]),
    (r"photography|摄影",                "MEDIA", ["PHOTOGRAPHY"]),
    # LAW
    (r"\blaw\b|legal|法律",              "LAW", ["LAW", "LEGAL_STUDIES"]),
    # PSYCHOLOGY / EDUCATION
    (r"psychology|心理",                 "PSYCHOLOGY", ["PSYCHOLOGY"]),
    (r"education|teaching|教育|师范",    "EDUCATION", ["EDUCATION", "TEACHING"]),
    # HOSPITALITY
    (r"culinary|chef|烹饪|厨师",         "HOSPITALITY", ["CULINARY"]),
    (r"hospitality|hotel|酒店",          "HOSPITALITY", ["HOSPITALITY_MANAGEMENT", "HOTEL_MANAGEMENT"]),
    (r"tourism|travel|旅游",             "HOSPITALITY", ["TOURISM"]),
]


def map_interest_to_subfield(interest: str) -> tuple[str | None, list[str]]:
    """Returns (sheet_tab, [allowed_sub_fields]) or (None, []) if unknown."""
    t = interest.lower()
    for pattern, tab, allowed in _SUB_MAP:
        if re.search(pattern, t):
            return tab, allowed
    return None, []
