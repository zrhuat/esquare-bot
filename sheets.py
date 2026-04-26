"""
Google Sheets read/write operations.
Uses gspread with service-account credentials.
"""
import json, time, logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDS_JSON, COURSE_SHEET_ID, DB_SHEET_ID, COURSE_TABS

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

_gc: gspread.Client | None = None
_course_cache: list[dict] = []
_course_cache_at: float = 0
CACHE_TTL = 300  # 5 minutes

_student_cache: dict[str, tuple[dict, float]] = {}
STUDENT_CACHE_TTL = 60  # 1 minute


def _client() -> gspread.Client:
    global _gc
    if _gc is None:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        _gc = gspread.authorize(creds)
    return _gc


# ── Student Tracking ──────────────────────────────────────────────────────────

def get_student(chat_id: str) -> dict:
    """Return student row from Student_Tracking, with 1-min in-memory cache."""
    global _student_cache
    cached, cached_at = _student_cache.get(chat_id, ({}, 0.0))
    if cached_at and time.time() - cached_at < STUDENT_CACHE_TTL:
        return cached
    try:
        sh = _client().open_by_key(DB_SHEET_ID)
        ws = sh.worksheet("Student_Tracking")
        records = ws.get_all_records()
        for row in records:
            if str(row.get("chat_id", "")).strip() == chat_id:
                _student_cache[chat_id] = (row, time.time())
                return row
    except Exception as e:
        logger.error("get_student error: %s", e)
    _student_cache[chat_id] = ({}, time.time())
    return {}


def update_student(chat_id: str, data: dict) -> None:
    """Upsert a student row in Student_Tracking (match on chat_id)."""
    global _student_cache
    try:
        sh = _client().open_by_key(DB_SHEET_ID)
        ws = sh.worksheet("Student_Tracking")
        headers = ws.row_values(1)

        col_a = ws.col_values(1)
        try:
            row_idx = col_a.index(chat_id) + 1
        except ValueError:
            row_idx = None

        data = {**data, "chat_id": chat_id, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        if row_idx:
            # Batch update all fields in one API call
            updates = []
            for col_name, value in data.items():
                if col_name in headers and value not in ("", None):
                    col_idx = headers.index(col_name) + 1
                    updates.append({
                        "range": gspread.utils.rowcol_to_a1(row_idx, col_idx),
                        "values": [[str(value)]],
                    })
            if updates:
                ws.batch_update(updates)
        else:
            row = [""] * len(headers)
            for col_name, value in data.items():
                if col_name in headers:
                    row[headers.index(col_name)] = str(value) if value is not None else ""
            ws.append_row(row, value_input_option="USER_ENTERED")

        # Update cache with new values
        cached, _ = _student_cache.get(chat_id, ({}, 0.0))
        merged = {**cached, **{k: v for k, v in data.items() if v not in ("", None)}}
        _student_cache[chat_id] = (merged, time.time())
    except Exception as e:
        logger.error("update_student error: %s", e)


def set_human_mode(chat_id: str, on: bool = True) -> None:
    update_student(chat_id, {"need_human": "YES" if on else ""})


# ── Student Registration ──────────────────────────────────────────────────────

def save_registration(chat_id: str, data: dict) -> None:
    """Append a new registration row to Student_Registration."""
    try:
        sh = _client().open_by_key(DB_SHEET_ID)
        ws = sh.worksheet("Student_Registration")
        headers = ws.row_values(1)
        row = [""] * len(headers)
        data = {**data, "chat_id": chat_id, "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "状态": "新申请"}
        for col_name, value in data.items():
            if col_name in headers:
                row[headers.index(col_name)] = str(value) if value is not None else ""
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error("save_registration error: %s", e)


# ── Course Database ───────────────────────────────────────────────────────────

def get_all_courses() -> list[dict]:
    """Load all courses from all tabs, with 5-min cache."""
    global _course_cache, _course_cache_at
    if _course_cache and time.time() - _course_cache_at < CACHE_TTL:
        return _course_cache

    courses = []
    try:
        sh = _client().open_by_key(COURSE_SHEET_ID)
        for tab in COURSE_TABS:
            try:
                ws = sh.worksheet(tab)
                rows = ws.get_all_records()
                for r in rows:
                    r["_tab"] = tab
                    courses.append(r)
            except Exception as e:
                logger.warning("Tab %s error: %s", tab, e)
        _course_cache = courses
        _course_cache_at = time.time()
        logger.info("Loaded %d courses from %d tabs", len(courses), len(COURSE_TABS))
    except Exception as e:
        logger.error("get_all_courses error: %s", e)

    return _course_cache


def query_courses(allowed_sub_fields: list[str], eligible_levels: list[str], tab: str | None = None) -> list[dict]:
    """Filter courses by sub_field and level. Return up to 3 (one per school)."""
    all_courses = get_all_courses()
    results = []
    seen_schools = set()

    for c in all_courses:
        if tab and c.get("_tab") != tab:
            continue
        sf = str(c.get("sub_field", "")).upper().strip()
        lv = str(c.get("level", "")).upper().strip()
        if allowed_sub_fields and sf not in allowed_sub_fields:
            continue
        if eligible_levels and lv not in eligible_levels:
            continue
        school = c.get("school_name", "")
        if school in seen_schools:
            continue
        seen_schools.add(school)
        results.append(c)
        if len(results) >= 3:
            break

    return results
