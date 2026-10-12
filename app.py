import streamlit as st
import os
import re
import sqlite3
import difflib
import json
import time
import zipfile
import concurrent.futures

st.set_page_config(
    page_title="מטמונים | מהדורת DBS למהדירי קבלה",
    page_icon="📜",
    layout="wide"
)

# --- עיצוב מותאם לעיון ממושך, בהיר ונקי ---
st.markdown("""
<style>
    @font-face {
        font-family: 'Assistant';
        src: url('app/static/Assistant.ttf') format('truetype');
        font-weight: 200 800;
        font-display: swap;
    }
    @font-face {
        font-family: 'Frank Ruhl Libre';
        src: url('app/static/FrankRuhlLibre.ttf') format('truetype');
        font-weight: 300 900;
        font-display: swap;
    }

    html, body, .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"] {
        font-family: 'Assistant', sans-serif !important;
        background-color: #f7f6f2 !important;
        color: #1c1917 !important;
        direction: rtl !important;
        text-align: right !important;
    }

    p, span, label, h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] {
        color: #1c1917 !important;
        direction: rtl !important;
        text-align: right !important;
    }

    h1, h2, h3 {
        font-family: 'Frank Ruhl Libre', serif !important;
        color: #0c0a09 !important;
        font-weight: 700 !important;
    }

    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e7e5e4 !important;
        border-radius: 14px !important;
        padding: 24px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03) !important;
    }

    .stTextInput input, .stNumberInput input, textarea {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        border: 1.5px solid #d6d3d1 !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="select"], div[data-baseweb="select"] * {
        background-color: #ffffff !important;
        color: #1c1917 !important;
    }

    .result-card {
        background: #ffffff !important;
        border: 1px solid #e7e5e4 !important;
        border-radius: 14px !important;
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02) !important;
    }

    .badge-book {
        display: inline-block;
        background-color: #eff6ff !important;
        color: #1e40af !important;
        font-weight: 700 !important;
        font-size: 13.5px !important;
        padding: 4px 12px !important;
        border-radius: 16px !important;
        border: 1px solid #dbeafe !important;
        margin-left: 6px !important;
    }

    .badge-author {
        display: inline-block;
        background-color: #f3e8ff !important;
        color: #6b21a8 !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 4px 10px !important;
        border-radius: 16px !important;
        border: 1px solid #e9d5ff !important;
        margin-left: 6px !important;
    }

    .badge-section {
        display: inline-block;
        background-color: #fef3c7 !important;
        color: #92400e !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 4px 10px !important;
        border-radius: 16px !important;
        border: 1px solid #fde68a !important;
        margin-left: 6px !important;
    }

    .snippet-text {
        font-size: 18px !important;
        line-height: 1.9 !important;
        color: #292524 !important;
        margin-top: 12px !important;
        padding-right: 14px !important;
        border-right: 3px solid #3b82f6 !important;
        text-align: justify !important;
    }

    .search-highlight {
        background-color: #fef08a !important;
        color: #000000 !important;
        font-weight: 800 !important;
        padding: 1px 4px !important;
        border-radius: 4px;
        border-bottom: 2px solid #ca8a04 !important;
    }

    .diff-del {
        background-color: #fee2e2 !important;
        color: #991b1b !important;
        text-decoration: line-through;
        padding: 2px 4px;
        border-radius: 4px;
    }
    .diff-add {
        background-color: #dcfce7 !important;
        color: #166534 !important;
        font-weight: 700;
        padding: 2px 4px;
        border-radius: 4px;
    }

    .stButton button {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        border: 1.5px solid #d6d3d1 !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    div[data-testid="stForm"] .stButton button {
        background-color: #1e3a8a !important;
        color: #ffffff !important;
        border: none !important;
    }
    div[data-testid="stForm"] .stButton button * {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

BOOKS_FOLDER = "books"
DB_FILE = "matmonim_dbs.db"
PARAS_PER_PAGE = 15
SCHEMA_VERSION = 6

if not os.path.exists(BOOKS_FOLDER):
    os.makedirs(BOOKS_FOLDER)

# אתחול Session State
for key, default in [
    ("app_mode", "🔍 חיפוש במאגר"),
    ("reader_author", "כל המחברים"),
    ("reader_category", "כל המדורים"),
    ("reader_book_path", None),
    ("reader_page", 1),
    ("reader_target_p", 0),
    ("reader_jump", None),
    ("reader_last_book", None),
    ("diff_text_a", ""),
    ("diff_text_b", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

KABBALAH_ACRONYMS = {
    "אדם קדמון": "א\"ק",
    "זעיר אנפין": "ז\"א",
    "אריך אנפין": "א\"א",
    "עתיק יומין": "ע\"י",
    "אבא ואמא": "או\"א",
    "ישראל סבא ותבונה": "ישסו\"ת",
    "עשר ספירות": "ע\"ס",
    "נצח הוד יסוד": "נה\"י",
    "נצח הוד יסוד מלכות": "נהי\"ם",
    "חכמה בינה דעת": "חב\"ד",
    "חסד גבורה תפארת": "חג\"ת",
    "שלוש ראשונות": "ג\"ר",
    "שלש ראשונות": "ג\"ר",
    "שבע תחתונות": "ז\"ת",
    "קודשא בריך הוא": "קוב\"ה",
    "אצילות בריאה יצירה עשיה": "אבי\"ע",
    "בריאה יצירה עשיה": "בי\"ע",
    "אור פנימי": "או\"פ",
    "אור מקיף": "או\"מ",
    "אור חוזר": "או\"ח",
    "אור ישר": "או\"י",
    "אור אינסוף": "אוא\"ס",
    "מיין נוקבין": "מ\"ן",
    "מיין דכורין": "מ\"ד",
    "נפש רוח נשמה חיה יחידה": "נרנח\"י",
    "עץ חיים": "ע\"ח",
    "פרי עץ חיים": "פע\"ח",
    "שער הכוונות": "שה\"כ",
    "שער הפסוקים": "שה\"פ",
    "שער הגלגולים": "שה\"ג",
    "שער רוח הקודש": "שרה\"ק",
    "מבוא שערים": "מבו\"ש",
    "אוצרות חיים": "אוצה\"ח",
    "רבי שמעון בר יוחאי": "רשב\"י",
    "רבי משה קורדובירו": "רמ\"ק",
    "רבי משה חיים לוצאטו": "רמח\"ל",
    "אדוננו רבי יצחק": "האר\"י",
    "רבי חיים ויטאל": "מהרח\"ו",
    "רבי שלום שרעבי": "הרש\"ש",
}

SECTION_RE = re.compile(
    r'^(?:(?:שער|ענף|פרק|סימן|סעיף|הלכה|דף|פתח|מאמר|חלק|אות|כלל)\s+([א-ת\d"״\'-]+|[א-ת]+(?:\s+[א-ת]+)?))',
    re.IGNORECASE
)

GEMATRIA_MAP = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40, 'נ': 50, 'ן': 50,
    'ס': 60, 'ע': 70, 'פ': 80, 'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100, 'ר': 200,
    'ש': 300, 'ת': 400
}

_strip_chars = {c: None for c in range(0x0591, 0x05C7 + 1)}
for q in ['"', "'", '״', '׳', '`', '”', '“', '’', '‘', '־', '-']:
    _strip_chars[ord(q)] = None

FAST_CLEAN_TRANS = str.maketrans(_strip_chars)

def fast_clean(text: str) -> str:
    return text.translate(FAST_CLEAN_TRANS)

def calculate_gematria(text):
    return sum(GEMATRIA_MAP.get(char, 0) for char in text)

def extract_author(title, path):
    full = (title + " " + path).lower()
    if any(w in full for w in ["זוהר", "זהר", "תיקוני", "תקוני", "ספרא דצניעותא", "אידרא", "רשב\"י", "רשבי", "שמעון בר יוחאי", "zohar"]):
        return "רבי שמעון בר יוחאי (רשב\"י)"
    if any(w in full for w in ["עץ חיים", "פרי עץ חיים", "כוונות", "הכוונות", "אוצרות חיים", "מבוא שערים", "שער הפסוקים", "שער הגלגולים", "שער מאמרי", "שער רוח הקודש", "ליקוטי תורה", "ויטאל", "מהרח\"ו", "מהרחו", "האר\"י", "הארי", "לוריא"]):
        return "האר\"י ומהרח\"ו"
    if any(w in full for w in ["פרדס", "פרדס רימונים", "אילימה", "תומר דבורה", "שיעור קומה", "אור יקר", "קורדובירו", "רמ\"ק", "רמק"]):
        return "רבי משה קורדובירו (רמ\"ק)"
    if any(w in full for w in ["פתחי חכמה", "דעת תבונות", "אדיר במרום", "רמח\"ל", "רמחל", "לוצאטו", "מאמר העיקרים", "קל\"ח", "דרך ה'"]):
        return "רבי משה חיים לוצאטו (רמח\"ל)"
    if any(w in full for w in ["אבולעפיה", "אבולעפיא"]):
        return "רבי אברהם אבולעפיה"
    if any(w in full for w in ["רמב\"ן", "רמבן", "נחמני"]):
        return "רבנו משה בן נחמן (רמב\"ן)"
    if any(w in full for w in ["שערי אורה", "גיקטיליא"]):
        return "רבי יוסף ג'יקטיליה"
    if any(w in full for w in ["גרנדה", "ברית מנוחה"]):
        return "רבי אברהם מגרנדה"
    if any(w in full for w in ["הגר\"א", "הגרא", "אליהו מוילנא"]):
        return "הגאון מווילנא (הגר\"א)"
    if any(w in full for w in ["בעש\"ט", "בעל שם טוב"]):
        return "הבעל שם טוב ותלמידיו"
    if any(w in full for w in ["תניא", "חב\"ד", "שניאור זלמן"]):
        return "רבי שניאור זלמן מלאדי (אדמו\"ר הזקן)"
    if any(w in full for w in ["יצירה"]):
        return "חז\"ל ומפרשי ספר יצירה"
    if any(w in full for w in ["בהיר"]):
        return "רבי נחוניא בן הקנה (ספר הבהיר)"
    return "מחברים שונים"

def classify_kabbalah_book(title, path):
    full = (title + " " + path).lower()
    if any(w in full for w in ["זוהר", "זהר", "תיקוני", "תקוני", "ספרא דצניעותא", "אידרא", "zohar"]):
        return "ספר הזוהר והתיקונים"
    if any(w in full for w in ["עץ חיים", "פרי עץ חיים", "כוונות", "הכוונות", "אוצרות חיים", "מבוא שערים", "שער הפסוקים", "שער הגלגולים", "שער מאמרי", "שער רוח הקודש", "ליקוטי תורה", "ויטאל", "האר\"י", "הארי"]):
        return "כתבי האר״י ומהרח״ו"
    if any(w in full for w in ["פרדס", "פרדס רימונים", "אילימה", "תומר דבורה", "שיעור קומה", "אור יקר", "קורדובירו", "רמ\"ק", "רמק"]):
        return "ספרי הרמ״ק"
    if any(w in full for w in ["פתחי חכמה", "דעת תבונות", "אדיר במרום", "רמח\"ל", "רמחל", "לוצאטו", "מאמר העיקרים", "קל\"ח", "דרך ה'"]):
        return "ספרי הרמח״ל"
    if any(w in full for w in ["יצירה", "ספר יצירה"]):
        return "ספר יצירה ומפרשיו"
    if any(w in full for w in ["בהיר", "הבהיר", "אבולעפיה", "אבולעפיא", "גרנדה", "ברית מנוחה", "רמב\"ן", "רקנאטי", "שערי אורה", "גיקטיליא", "רזיאל"]):
        return "קבלה קדומה וראשונים"
    if any(w in full for w in ["בעש\"ט", "בעל שם טוב", "תניא", "חב\"ד", "חבד", "ליקוטי מוהר\"ן", "ברסלב", "קדושת לוי", "שפת אמת", "בני יששכר"]):
        return "ספרי חסידות ופנימיות"
    return "ספרי קבלה ודרוש"

def extract_title_and_clean_text(raw_content, file_path):
    title = None
    title_match = re.search(r'<title>(.*?)</title>', raw_content[:3000], re.IGNORECASE)
    if title_match:
        t_clean = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        if t_clean and any('\u0590' <= c <= '\u05FF' for c in t_clean):
            title = t_clean

    clean_content = re.sub(r'<[^>]+>', ' ', raw_content)
    clean_content = clean_content.replace('\r\n', '\n').replace('\r', '\n')

    if not title:
        lines = [line.strip() for line in clean_content.split('\n') if line.strip()][:10]
        for line in lines:
            if any('\u0590' <= c <= '\u05FF' for c in line) and len(line) <= 70:
                title = line
                break

    if not title:
        title = os.path.splitext(os.path.basename(file_path))[0]

    return title.strip(), clean_content

# =========================================================
# הגדרות SQLite למאגרי ענק
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=60000;")
    conn.execute("PRAGMA cache_size=-64000;")
    conn.execute("PRAGMA mmap_size=268435456;")
    return conn

def init_dbs_engine():
    if os.path.exists(DB_FILE):
        try:
            test_conn = sqlite3.connect(DB_FILE)
            v = test_conn.execute("PRAGMA user_version;").fetchone()[0]
            test_conn.close()
            if v < SCHEMA_VERSION:
                for ext in ["", "-wal", "-shm"]:
                    f_to_del = DB_FILE + ext
                    if os.path.exists(f_to_del):
                        os.remove(f_to_del)
        except Exception:
            pass

    conn = get_db_connection()
    c = conn.cursor()

    c.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")

    c.execute("""
    CREATE TABLE IF NOT EXISTS books_meta (
        path TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        category TEXT,
        total_paras INTEGER,
        toc_json TEXT,
        mtime REAL
    );
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS paragraphs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_path TEXT,
        sec_name TEXT,
        p_num INTEGER,
        raw_text TEXT
    );
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_para_book_p ON paragraphs(book_path, p_num);")

    c.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS dbs_index USING fts5(
        clean_text,
        tokenize='unicode61'
    );
    """)

    conn.commit()
    conn.close()

def remove_book_rows(c, clean_path):
    c.execute("""
    DELETE FROM dbs_index WHERE rowid IN (
        SELECT id FROM paragraphs WHERE book_path = ?
    );
    """, (clean_path,))
    c.execute("DELETE FROM paragraphs WHERE book_path = ?;", (clean_path,))

# פונקציית עזר לעיבוד קובץ בודד
def _parse_single_file(item):
    filepath, clean_path, mtime = item
    try:
        raw_content = ""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='cp1255', errors='ignore') as f:
                raw_content = f.read()

        book_title, clean_content = extract_title_and_clean_text(raw_content, filepath)
        category = classify_kabbalah_book(book_title, clean_path)
        author = extract_author(book_title, clean_path)

        raw_lines = [line.strip() for line in clean_content.split('\n') if line.strip()]

        paras = []
        sections = []
        toc = []
        current_sec = "פתיחה"
        buf = []
        buf_len = 0

        for line in raw_lines:
            m_sec = SECTION_RE.match(line)
            is_header = bool(m_sec) or (len(line) <= 40 and any(w in line for w in ["שער", "ענף", "פרק", "דף", "פתח", "סימן", "סעיף", "הלכה"]))

            if is_header:
                if buf:
                    paras.append(" ".join(buf))
                    sections.append(current_sec)
                    buf = []
                    buf_len = 0

                current_sec = line[:50]
                if current_sec not in [t[0] for t in toc]:
                    toc.append((current_sec, len(paras)))
                buf.append(line)
                buf_len += len(line)
                continue

            buf.append(line)
            buf_len += len(line)

            if buf_len >= 550:
                paras.append(" ".join(buf))
                sections.append(current_sec)
                buf = []
                buf_len = 0

        if buf:
            paras.append(" ".join(buf))
            sections.append(current_sec)

        cleaned_paras = [fast_clean(p) for p in paras]
        meta = (clean_path, book_title, author, category, len(paras), json.dumps(toc, ensure_ascii=False), mtime)

        return {
            "meta": meta,
            "clean_path": clean_path,
            "book_title": book_title,
            "author": author,
            "paras": paras,
            "sections": sections,
            "cleaned_paras": cleaned_paras
        }
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def build_or_update_index():
    init_dbs_engine()
    conn = get_db_connection()
    c = conn.cursor()

    existing_rows = c.execute("SELECT path, mtime FROM books_meta").fetchall()
    existing_map = {row[0]: row[1] for row in existing_rows}

    txt_files = []
    for root, dirs, files in os.walk(BOOKS_FOLDER):
        for f in files:
            if f.endswith(".txt"):
                txt_files.append(os.path.join(root, f))

    need_index = []
    for f in txt_files:
        clean_p = os.path.splitext(os.path.relpath(f, BOOKS_FOLDER))[0].replace("\\", " / ")
        mtime = os.path.getmtime(f)
        if clean_p not in existing_map or existing_map[clean_p] != mtime:
            need_index.append((f, clean_p, mtime))

    if need_index:
        total_files = len(need_index)
        progress_slot = st.empty()
        status_slot = st.empty()
        status_slot.info(f"⚡ מאנדקס בטורבו {total_files} ספרים...")
        prog_bar = progress_slot.progress(0.0)

        # הגדרות ביצועים מירביות ל-SQLite בזמן אנדוקס
        c.execute("PRAGMA synchronous = OFF;")
        c.execute("PRAGMA temp_store = MEMORY;")
        c.execute("PRAGMA cache_size = -128000;")

        cur_id = c.execute("SELECT COALESCE(MAX(id), 0) FROM paragraphs;").fetchone()[0]

        processed_count = 0
        last_ui_update = time.time()

        c.execute("BEGIN TRANSACTION;")

        # שימוש ב-ThreadPoolExecutor (בטוח לחלוטין ב-Windows וטוען במקביל מהדיסק)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for parsed in executor.map(_parse_single_file, need_index):
                if not parsed:
                    continue

                clean_path = parsed["clean_path"]
                if clean_path in existing_map:
                    remove_book_rows(c, clean_path)

                paras = parsed["paras"]
                sections = parsed["sections"]
                cleaned_paras = parsed["cleaned_paras"]

                para_rows = []
                fts_rows = []

                for i, p_raw in enumerate(paras):
                    cur_id += 1
                    para_rows.append((cur_id, clean_path, sections[i], i + 1, p_raw))
                    fts_rows.append((cur_id, cleaned_paras[i]))

                c.executemany("INSERT INTO paragraphs(id, book_path, sec_name, p_num, raw_text) VALUES (?, ?, ?, ?, ?);", para_rows)
                c.executemany("INSERT INTO dbs_index(rowid, clean_text) VALUES (?, ?);", fts_rows)

                c.execute("""
                INSERT OR REPLACE INTO books_meta(path, title, author, category, total_paras, toc_json, mtime)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, parsed["meta"])

                processed_count += 1

                if processed_count % 100 == 0:
                    c.execute("COMMIT;")
                    c.execute("BEGIN TRANSACTION;")

                now = time.time()
                if now - last_ui_update > 0.4 or processed_count == total_files:
                    prog_bar.progress(processed_count / total_files)
                    status_slot.caption(f"מאנדקס ({processed_count}/{total_files}): **{parsed['book_title']}** [{parsed['author']}]")
                    last_ui_update = now

        c.execute("COMMIT;")
        c.execute("PRAGMA synchronous = NORMAL;")
        progress_slot.empty()
        status_slot.empty()

    conn.close()
    return True

# --- בונה שאילתת DBS: מילה שלמה בלבד ---
PREFIX_LIST = [
    "", "ו", "ד", "ש", "ה", "ב", "כ", "ל", "מ",
    "וד", "וש", "וה", "וב", "וכ", "ול", "ומ",
    "שב", "של", "שמ", "שכ", "שה"
]

def build_dbs_query(query, search_mode, allow_prefixes, allow_acronyms, exclude_query=""):
    words = [w.strip() for w in query.split() if w.strip()]
    if not words:
        return ""

    def process_token(tok):
        has_wildcard = tok.endswith('*')
        base = fast_clean(tok.rstrip('*'))
        if not base:
            return ""

        variants = [base]
        if allow_acronyms:
            for full_term, acr in KABBALAH_ACRONYMS.items():
                c_acr = fast_clean(acr)
                c_full = fast_clean(full_term)
                if base == c_acr and c_full not in variants:
                    variants.append(c_full)
                elif base == c_full and c_acr not in variants:
                    variants.append(c_acr)

        sub_parts = []
        for v in variants:
            if ' ' in v:
                if allow_prefixes:
                    v_words = v.split()
                    first_w = v_words[0]
                    rest = " ".join(v_words[1:])
                    phrase_variants = [f'"{pref}{first_w} {rest}"' for pref in ["", "ו", "ד", "ש", "ה", "ב", "ל", "כ", "מ"]]
                    sub_parts.append("(" + " OR ".join(phrase_variants) + ")")
                else:
                    sub_parts.append(f'"{v}"')
            elif has_wildcard:
                sub_parts.append(f'{v}*')
            else:
                if allow_prefixes:
                    pref_parts = [f'"{pref}{v}"' for pref in PREFIX_LIST]
                    sub_parts.append("(" + " OR ".join(pref_parts) + ")")
                else:
                    sub_parts.append(f'"{v}"')

        if len(sub_parts) > 1:
            return "(" + " OR ".join(sub_parts) + ")"
        return sub_parts[0]

    processed = [process_token(w) for w in words if process_token(w)]
    if not processed:
        return ""

    if search_mode == "ביטוי מדויק":
        fts_q = f'"{fast_clean(query)}"'
    elif search_mode == "לפחות אחת (או)":
        fts_q = " OR ".join(processed)
    else:
        fts_q = " AND ".join(processed)

    if exclude_query.strip():
        ex_words = [fast_clean(w) for w in exclude_query.split() if w.strip()]
        for ex in ex_words:
            fts_q += f' NOT "{ex}"'

    return fts_q

def make_flexible_hebrew_pattern(term: str, wildcard: bool = False) -> str:
    NIQQUD_AND_QUOTES = r'[\u0591-\u05C7"\'״׳`\-]*'
    PREFIXES = r'(?:[ומשכלבהד][\u0591-\u05C7]*){0,3}'

    words = term.split()
    word_patterns = []
    for w in words:
        letters = list(w)
        if not letters:
            continue
        char_pat = NIQQUD_AND_QUOTES.join(re.escape(ch) for ch in letters) + NIQQUD_AND_QUOTES
        word_patterns.append(char_pat)

    if not word_patterns:
        return ""

    phrase_pat = r'[\s\-]+'.join(word_patterns)

    if wildcard:
        return rf'(?<![א-ת]){PREFIXES}{phrase_pat}[א-ת\u0591-\u05C7]*'
    else:
        return rf'(?<![א-ת]){PREFIXES}{phrase_pat}(?![א-ת])'

def highlight_dbs_matches(text, query_words, allow_acronyms):
    if not query_words:
        return text

    terms_to_find = set()
    for w in query_words:
        has_wildcard = w.endswith('*')
        clean_w = fast_clean(w.rstrip('*'))
        if clean_w:
            terms_to_find.add((clean_w, has_wildcard))
            if allow_acronyms:
                for full_t, acr in KABBALAH_ACRONYMS.items():
                    c_acr = fast_clean(acr)
                    c_full = fast_clean(full_t)
                    if clean_w == c_acr:
                        terms_to_find.add((c_full, False))
                    elif clean_w == c_full:
                        terms_to_find.add((c_acr, False))

    if not terms_to_find:
        return text

    sorted_terms = sorted(list(terms_to_find), key=lambda x: len(x[0]), reverse=True)

    patterns = []
    for term, wildcard in sorted_terms:
        pat = make_flexible_hebrew_pattern(term, wildcard)
        if pat:
            patterns.append(pat)

    if not patterns:
        return text

    combined_regex = "(" + "|".join(patterns) + ")"
    try:
        return re.sub(combined_regex, r'<span class="search-highlight">\g<0></span>', text)
    except Exception:
        return text

def check_proximity_in_text(raw_text, query_words, max_distance):
    tokens = [fast_clean(t) for t in raw_text.split() if t]
    positions = []
    for w in query_words:
        target = fast_clean(w.rstrip('*'))
        pos_list = [i for i, tok in enumerate(tokens) if target in tok]
        if not pos_list:
            return False
        positions.append(pos_list)

    min_span = 999999
    import itertools
    for combo in itertools.product(*positions):
        span = max(combo) - min(combo)
        if span < min_span:
            min_span = span
    return min_span <= max_distance

# הפעלת אינדקס
build_or_update_index()
conn = get_db_connection()

books_meta_rows = conn.execute("SELECT path, title, category, total_paras, toc_json, author FROM books_meta ORDER BY title").fetchall()
books_by_path = {row[0]: {"title": row[1], "category": row[2], "total": row[3], "toc": row[4], "author": row[5]} for row in books_meta_rows}

all_categories = sorted(list(set(b["category"] for b in books_by_path.values()))) if books_by_path else []
all_authors = sorted(list(set(b["author"] for b in books_by_path.values()))) if books_by_path else []

# --- סרגל צד ---
with st.sidebar:
    st.markdown("### ⚡ מאגר ענק (DBS)")
    st.markdown(f"**ספרים באינדקס המהיר:** `{len(books_by_path)}`")
    st.markdown(f"**מחברים מזוהים:** `{len(all_authors)}`")
    st.markdown(f"**מדורים במאגר:** `{len(all_categories)}`")

    if st.button("🔄 בנה מחדש אינדקס מלא", use_container_width=True):
        conn.close()
        for ext in ["", "-wal", "-shm"]:
            fpath = DB_FILE + ext
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
        st.cache_resource.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("#### 📥 הוספת ספרים")
    uploaded_files = st.file_uploader("העלאת קובצי TXT או ZIP:", type=["txt", "zip"], accept_multiple_files=True)
    if uploaded_files:
        added = 0
        for uf in uploaded_files:
            if uf.name.endswith(".zip"):
                with zipfile.ZipFile(uf, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            z.extract(filename, BOOKS_FOLDER)
                            added += 1
            elif uf.name.endswith(".txt"):
                fpath = os.path.join(BOOKS_FOLDER, uf.name)
                with open(fpath, "wb") as f:
                    f.write(uf.getbuffer())
                added += 1
        if added > 0:
            st.success(f"נוספו {added} ספרים! מעדכן אינדקס...")
            st.cache_resource.clear()
            st.rerun()

# --- כותרת ומעבר מצבים ---
header_col1, header_col2 = st.columns([2, 1.2])
with header_col1:
    st.markdown("# 💎 מַטְמוֹנִים · מהדורת המהדיר")
    st.caption("מנוע DBS למאגרי ענק (2,000+ ספרים) · פילוח מחברים ומדורים · שולחן המהדיר")

with header_col2:
    mode_options = ["🔍 חיפוש במאגר", "📖 בית מדרש לעיון", "✍️ שולחן המהדיר"]
    current_idx = mode_options.index(st.session_state["app_mode"]) if st.session_state["app_mode"] in mode_options else 0
    mode_choice = st.radio(
        "מצב עבודה:",
        mode_options,
        horizontal=True,
        index=current_idx,
        label_visibility="collapsed"
    )
    st.session_state["app_mode"] = mode_choice

st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

# ==========================================
# מצב 1: חיפוש במאגר (DBS Grade Search)
# ==========================================
if st.session_state["app_mode"] == "🔍 חיפוש במאגר":
    filt_col1, filt_col2, filt_col3 = st.columns([1.5, 1.5, 3])
    with filt_col1:
        author_filter = st.selectbox("מחבר:", options=["כל המחברים"] + all_authors, index=0)
    with filt_col2:
        cat_filter = st.selectbox("מדור קבלי:", options=["הכל"] + all_categories, index=0)
    with filt_col3:
        available_books_search = [
            k for k in books_by_path.keys() 
            if (author_filter == "כל המחברים" or books_by_path[k]["author"] == author_filter)
            and (cat_filter == "הכל" or books_by_path[k]["category"] == cat_filter)
        ]
        sorted_keys = sorted(available_books_search, key=lambda k: books_by_path[k]['title'])
        selected_search_book = st.selectbox(
            "ספר מסוים (אופציונלי):",
            options=sorted_keys,
            index=None,
            placeholder="🔍 בחר ספר לחיפוש ממוקד... (או השאר ריק)",
            format_func=lambda k: f"{books_by_path[k]['title']} · [{books_by_path[k]['author']}]"
        )

    with st.form("search_form"):
        col_q, col_ex = st.columns([4, 2])
        with col_q:
            query = st.text_input("שאילתת חיפוש DBS (מילים שלמות):", placeholder="הקלד מילים (למשל: ז\"א , אדם קדמון , ספיר*)...")
        with col_ex:
            exclude_query = st.text_input("החרג מילים (NOT):", placeholder="מילים שלא יופיעו...")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            allow_prefixes = st.checkbox("אותיות שימוש תקניות (ומשכלב\"ד)", value=True)
        with c2:
            allow_acronyms = st.checkbox("פענוח קיצורי קבלה חכם", value=True)
        with c3:
            search_mode = st.selectbox("אופן החיפוש:", ["כל המילים (וגם)", "מרחק בין מילים", "ביטוי מדויק", "לפחות אחת (או)"])
        with c4:
            limit_choice = st.selectbox("מגבלת תוצאות:", ["500", "1,000", "2,000", "5,000", "ללא הגבלה"], index=1)

        max_distance = 7
        if search_mode == "מרחק בין מילים":
            max_distance = st.slider("מרחק מילים מקסימלי (NEAR):", 1, 40, 7)

        submitted = st.form_submit_button("⚡ חפש במהירות הבזק", use_container_width=True)

    if query and (submitted or "last_query" in st.session_state):
        st.session_state["last_query"] = query
        t_start = time.time()

        fts_expression = build_dbs_query(query, search_mode, allow_prefixes, allow_acronyms, exclude_query)

        limit_map = {"500": 500, "1,000": 1000, "2,000": 2000, "5,000": 5000, "ללא הגבלה": 50000}
        max_rows = limit_map.get(limit_choice, 1000)

        sql_base = """
        SELECT p.book_path, b.title, b.author, b.category, b.total_paras, p.sec_name, p.p_num, p.raw_text
        FROM dbs_index d
        JOIN paragraphs p ON d.rowid = p.id
        JOIN books_meta b ON p.book_path = b.path
        WHERE d.clean_text MATCH ?
        """
        params = [fts_expression]

        if selected_search_book:
            sql_base += " AND p.book_path = ?"
            params.append(selected_search_book)

        if author_filter != "כל המחברים":
            sql_base += " AND b.author = ?"
            params.append(author_filter)

        if cat_filter != "הכל":
            sql_base += " AND b.category = ?"
            params.append(cat_filter)

        sql_base += " LIMIT ?;"
        params.append(max_rows)

        results = []
        try:
            cur = conn.cursor()
            cur.execute(sql_base, params)
            raw_hits = cur.fetchall()

            q_words = [w.strip() for w in query.split() if w.strip()]

            for h in raw_hits:
                if search_mode == "מרחק בין מילים" and len(q_words) >= 2:
                    if not check_proximity_in_text(h[7], q_words, max_distance):
                        continue

                results.append({
                    "book_path": h[0],
                    "title": h[1],
                    "author": h[2],
                    "category": h[3],
                    "total_p": h[4],
                    "section": h[5],
                    "p_num": h[6],
                    "raw_text": h[7]
                })
        except sqlite3.OperationalError as e:
            st.error(f"שגיאת תחביר בחיפוש: {e}")

        elapsed = time.time() - t_start
        total_results = len(results)

        if total_results == max_rows and limit_choice != "ללא הגבלה":
            st.markdown(f"#### נמצאו `{total_results}` תוצאות (הוגבל ל-{limit_choice} הראשונות) בתוך `{elapsed:.3f}` שניות")
        else:
            st.markdown(f"#### נמצאו `{total_results}` תוצאות בתוך `{elapsed:.3f}` שניות (מהירות DBS)")

        if total_results > 0:
            PAGE_SIZE = 20
            total_pages = max(1, (total_results + PAGE_SIZE - 1) // PAGE_SIZE)
            p_col1, p_col2 = st.columns([1, 4])
            with p_col1:
                current_page = st.number_input(f"עמוד (מתוך {total_pages}):", 1, total_pages, 1, key="res_page")

            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, total_results)

            q_words = [w.strip() for w in query.split() if w.strip()]

            for idx, r in enumerate(results[start_idx:end_idx]):
                snippet = highlight_dbs_matches(r["raw_text"], q_words, allow_acronyms)
                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span class="badge-book">📖 {r['title']}</span>
                            <span class="badge-author">✍️ {r['author']}</span>
                            <span class="badge-section">📍 {r['section']}</span>
                            <span style="font-size: 13px; color: #57534e;">מדור: {r['category']}</span>
                        </div>
                        <span style="font-size: 13px; color: #78716c; font-weight: 600;">פסקה {r['p_num']} מתוך {r['total_p']}</span>
                    </div>
                    <div class="snippet-text">
                        {snippet}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                btn1, btn2, btn3, btn4 = st.columns([1, 1.4, 1.4, 2])
                with btn1:
                    if st.button("📖 פתח לעיון", key=f"open_reader_{start_idx + idx}", use_container_width=True):
                        st.session_state["app_mode"] = "📖 בית מדרש לעיון"
                        st.session_state["reader_author"] = r["author"]
                        st.session_state["reader_category"] = r["category"]
                        st.session_state["reader_book_path"] = r["book_path"]
                        st.session_state["reader_target_p"] = r["p_num"]
                        st.session_state["reader_jump"] = (r["p_num"] - 1) // PARAS_PER_PAGE + 1
                        st.rerun()

                with btn2:
                    with st.popover("📋 העתק למהדורה"):
                        footnote_citation = f'[{r["title"]}, {r["section"]}]: "{r["raw_text"].strip()}"'
                        st.text_area("ציטוט להערת שוליים:", footnote_citation, height=90)

                with btn3:
                    if st.button("⚖️ שלח לשולחן ההשוואה", key=f"send_diff_{start_idx + idx}", use_container_width=True):
                        st.session_state["diff_text_a"] = r["raw_text"]
                        st.session_state["app_mode"] = "✍️ שולחן המהדיר"
                        st.toast("הקטע נשלח להשוואת נוסחאות!")
                        st.rerun()

                with btn4:
                    with st.expander("🔍 הצג הקשר מורחב"):
                        cur = conn.cursor()
                        cur.execute("""
                        SELECT p_num, raw_text FROM paragraphs 
                        WHERE book_path = ? AND p_num IN (?, ?)
                        ORDER BY p_num ASC;
                        """, (r["book_path"], r["p_num"] - 1, r["p_num"] + 1))
                        neighbors = {row[0]: row[1] for row in cur.fetchall()}

                        if (r["p_num"] - 1) in neighbors:
                            st.markdown(f"<p style='color: #57534e; font-size: 14.5px;'>[{r['p_num'] - 1}] {neighbors[r['p_num'] - 1]}</p>", unsafe_allow_html=True)
                        st.markdown(f"<div style='background-color: #fefce8; border-right: 4px solid #eab308; padding: 10px; border-radius: 6px; margin: 6px 0;'>{snippet}</div>", unsafe_allow_html=True)
                        if (r["p_num"] + 1) in neighbors:
                            st.markdown(f"<p style='color: #57534e; font-size: 14.5px;'>[{r['p_num'] + 1}] {neighbors[r['p_num'] + 1]}</p>", unsafe_allow_html=True)

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# ==========================================
# מצב 2: בית מדרש לעיון (עם קפיצה למראה מקום)
# ==========================================
elif st.session_state["app_mode"] == "📖 בית מדרש לעיון":
    if not books_by_path:
        st.warning("אין עדיין ספרים באינדקס.")
    else:
        with st.expander("🎯 קפיצה ישירה למקור (לפי ספר, פרק, שער, סימן, סעיף, דף או מחבר)", expanded=False):
            jump_c1, jump_c2 = st.columns([5, 1])
            with jump_c1:
                jump_input = st.text_input("הקלד מראה מקום:", placeholder="למשל: עץ חיים שער א ענף ב | פרדס שער כג | רמח\"ל פתחי חכמה פתח ה | דף יד")
            with jump_c2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                do_jump = st.button("קפוץ ישירות 🚀", use_container_width=True)

            if do_jump and jump_input.strip():
                clean_jump = fast_clean(jump_input)
                matched_book_path = None
                
                for b_path, b_info in books_by_path.items():
                    c_title = fast_clean(b_info["title"])
                    if c_title in clean_jump or any(w in clean_jump for w in c_title.split() if len(w) >= 3):
                        matched_book_path = b_path
                        break

                if not matched_book_path:
                    matched_book_path = st.session_state.get("reader_book_path") or list(books_by_path.keys())[0]

                cur = conn.cursor()
                sec_match = SECTION_RE.search(jump_input)
                target_sec_keyword = sec_match.group(0) if sec_match else jump_input

                cur.execute("""
                SELECT p_num, sec_name FROM paragraphs 
                WHERE book_path = ? AND sec_name LIKE ? 
                LIMIT 1;
                """, (matched_book_path, f"%{target_sec_keyword}%"))
                jump_res = cur.fetchone()

                if not jump_res:
                    cur.execute("""
                    SELECT p_num, sec_name FROM paragraphs 
                    WHERE book_path = ? AND raw_text LIKE ? 
                    LIMIT 1;
                    """, (matched_book_path, f"%{target_sec_keyword}%"))
                    jump_res = cur.fetchone()

                if jump_res:
                    p_target = jump_res[0]
                    st.session_state["reader_book_path"] = matched_book_path
                    st.session_state["reader_target_p"] = p_target
                    st.session_state["reader_jump"] = (p_target - 1) // PARAS_PER_PAGE + 1
                    st.toast(f"נמצא: {books_by_path[matched_book_path]['title']} · {jump_res[1]}")
                    st.rerun()
                else:
                    st.warning("לא נמצא מראה מקום תואם. נסה לפרט שם שער, ענף או פרק מדויקים.")

        col_auth, col_cat, col_book, col_toc, col_font = st.columns([1.3, 1.3, 2, 1.8, 0.8])

        with col_auth:
            auth_opts = ["כל המחברים"] + all_authors
            cur_auth_idx = auth_opts.index(st.session_state["reader_author"]) if st.session_state["reader_author"] in auth_opts else 0
            selected_reader_auth = st.selectbox("מחבר:", options=auth_opts, index=cur_auth_idx)
            st.session_state["reader_author"] = selected_reader_auth

        with col_cat:
            cat_opts = ["כל המדורים"] + all_categories
            cur_cat_idx = cat_opts.index(st.session_state["reader_category"]) if st.session_state["reader_category"] in cat_opts else 0
            selected_reader_cat = st.selectbox("מדור:", options=cat_opts, index=cur_cat_idx)
            st.session_state["reader_category"] = selected_reader_cat

        available_reader_books = [
            k for k in books_by_path.keys()
            if (selected_reader_auth == "כל המחברים" or books_by_path[k]["author"] == selected_reader_auth)
            and (selected_reader_cat == "כל המדורים" or books_by_path[k]["category"] == selected_reader_cat)
        ]
        sorted_reader_keys = sorted(available_reader_books, key=lambda k: books_by_path[k]['title'])

        if not sorted_reader_keys:
            st.info("אין ספרים התואמים את הסינון שנבחר.")
        else:
            default_book_idx = 0
            if st.session_state.get("reader_book_path") in sorted_reader_keys:
                default_book_idx = sorted_reader_keys.index(st.session_state["reader_book_path"])

            with col_book:
                selected_reader_path = st.selectbox(
                    "ספר נוכחי:",
                    options=sorted_reader_keys,
                    index=default_book_idx,
                    format_func=lambda k: f"{books_by_path[k]['title']}"
                )
                st.session_state["reader_book_path"] = selected_reader_path

            current_meta = books_by_path[selected_reader_path]
            total_paras = current_meta["total"]
            total_pages = max(1, (total_paras + PARAS_PER_PAGE - 1) // PARAS_PER_PAGE)

            toc = json.loads(current_meta["toc"]) if current_meta["toc"] else []

            with col_toc:
                if toc:
                    toc_labels = [f"{t[0]} (פסקה {t[1] + 1})" for t in toc]
                    jump_toc = st.selectbox("שער / פרק:", options=["בחר לקפיצה..."] + toc_labels)
                    if jump_toc != "בחר לקפיצה...":
                        chosen_idx = toc_labels.index(jump_toc)
                        target_p_num = toc[chosen_idx][1] + 1
                        st.session_state["reader_page"] = (target_p_num - 1) // PARAS_PER_PAGE + 1
                        st.session_state["reader_target_p"] = target_p_num
                else:
                    st.caption("אין תוכן שערים מזוהה")

            with col_font:
                font_size = st.slider("כתב:", 16, 32, 20)

            if st.session_state.get("reader_jump") is not None:
                st.session_state["reader_page"] = min(st.session_state["reader_jump"], total_pages)
                st.session_state["reader_jump"] = None
            elif st.session_state.get("reader_last_book") != selected_reader_path:
                st.session_state["reader_page"] = 1
                st.session_state["reader_target_p"] = 0
            st.session_state["reader_last_book"] = selected_reader_path
            st.session_state["reader_page"] = max(1, min(st.session_state.get("reader_page", 1), total_pages))

            def go_prev():
                st.session_state["reader_page"] = max(1, st.session_state["reader_page"] - 1)
                st.session_state["reader_target_p"] = 0

            def go_next():
                st.session_state["reader_page"] = min(total_pages, st.session_state["reader_page"] + 1)
                st.session_state["reader_target_p"] = 0

            st.markdown(f"""
            <div style="background: #ffffff; border: 1px solid #e7e5e4; border-radius: 14px; padding: 16px 24px; margin-bottom: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <h2 style="margin: 0; color: #0c0a09; font-family: 'Frank Ruhl Libre', serif;">{current_meta['title']}</h2>
                <div style="margin-top: 4px;">
                    <span class="badge-author">✍️ {current_meta['author']}</span>
                    <span style="font-size: 13.5px; color: #78716c; font-weight: 600;">מדור: {current_meta['category']} · מיקום: {selected_reader_path} · {total_paras} פסקאות</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                st.button("⬅️ עמוד קודם", use_container_width=True, key="t_prev", disabled=(st.session_state["reader_page"] <= 1), on_click=go_prev)
            with nav2:
                page_val = st.number_input(
                    f"עמוד (מתוך {total_pages}):",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state["reader_page"],
                    step=1,
                    key="reader_page_input"
                )
                st.session_state["reader_page"] = page_val
            with nav3:
                st.button("עמוד הבא ➡️", use_container_width=True, key="t_next", disabled=(st.session_state["reader_page"] >= total_pages), on_click=go_next)

            cur_p_start = (st.session_state["reader_page"] - 1) * PARAS_PER_PAGE + 1
            cur_p_end = cur_p_start + PARAS_PER_PAGE - 1

            cur = conn.cursor()
            cur.execute("""
            SELECT p_num, sec_name, raw_text
            FROM paragraphs
            WHERE book_path = ? AND p_num BETWEEN ? AND ?
            ORDER BY p_num ASC;
            """, (selected_reader_path, cur_p_start, cur_p_end))
            page_paras = cur.fetchall()

            target_p = st.session_state.get("reader_target_p", 0)

            st.markdown("<div style='max-width: 900px; margin: 0 auto; background: #ffffff; border: 1px solid #e7e5e4; border-radius: 16px; padding: 32px 42px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);'>", unsafe_allow_html=True)

            for p_row in page_paras:
                para_num = int(p_row[0])
                sec_name = p_row[1]
                p_text = p_row[2]

                if para_num == target_p:
                    st.markdown(f"""
                    <div style="background-color: #fefce8; border-right: 5px solid #eab308; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
                        <span style="font-size: 13px; color: #854d0e; font-weight: 800;">📍 פסקה {para_num} [{sec_name}]:</span>
                        <div style="font-size: {font_size}px; line-height: 1.95; margin-top: 6px; color: #0c0a09; text-align: justify; font-weight: 600;">{p_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="margin-bottom: 22px; padding-bottom: 14px; border-bottom: 1px solid #f5f5f4;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-size: 12.5px; color: #a8a29e; font-weight: 800;">[{para_num}]</span>
                            <span style="font-size: 12px; color: #b45309; font-weight: 600;">{sec_name}</span>
                        </div>
                        <div style="font-size: {font_size}px; line-height: 1.95; color: #292524; text-align: justify;">{p_text}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1, 2, 1])
            with b1:
                st.button("⬅️ עמוד קודם ", key="b_prev", use_container_width=True, disabled=(st.session_state["reader_page"] <= 1), on_click=go_prev)
            with b3:
                st.button("עמוד הבא ➡️ ", key="b_next", use_container_width=True, disabled=(st.session_state["reader_page"] >= total_pages), on_click=go_next)

# ==========================================
# מצב 3: ✍️ שולחן המהדיר
# ==========================================
else:
    st.markdown("### ✍️ שולחן המהדיר · כלי עריכה, השוואה וגימטריה")
    st.caption("כלים מתקדמים למאגרי ענק (2,000+ ספרים)")

    tab_diff, tab_gematria = st.tabs(["⚖️ השוואת נוסחאות וכתבי יד (Diff)", "🔢 מחשבון ואיתור גימטריאות"])

    with tab_diff:
        st.markdown("##### השוואת שני נוסחים (דפוס מול כתב יד / מהדורא קמא מול תנינא)")
        diff_col1, diff_col2 = st.columns(2)
        with diff_col1:
            text_a = st.text_area("נוסח א' (דפוס ראשון / נוסח הבסיס):", value=st.session_state.get("diff_text_a", ""), height=180)
        with diff_col2:
            text_b = st.text_area("נוסח ב' (כתב יד / מהדורה שונה):", value=st.session_state.get("diff_text_b", ""), height=180)

        if text_a.strip() and text_b.strip():
            words_a = text_a.split()
            words_b = text_b.split()
            matcher = difflib.SequenceMatcher(None, words_a, words_b)
            res_a = []
            res_b = []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    chunk = " ".join(words_a[i1:i2])
                    res_a.append(chunk)
                    res_b.append(chunk)
                elif tag == 'delete':
                    chunk = " ".join(words_a[i1:i2])
                    res_a.append(f'<span class="diff-del">{chunk}</span>')
                elif tag == 'insert':
                    chunk = " ".join(words_b[j1:j2])
                    res_b.append(f'<span class="diff-add">{chunk}</span>')
                elif tag == 'replace':
                    ca = " ".join(words_a[i1:i2])
                    cb = " ".join(words_b[j1:j2])
                    res_a.append(f'<span class="diff-del">{ca}</span>')
                    res_b.append(f'<span class="diff-add">{cb}</span>')

            st.markdown("---")
            st.markdown("#### 🔍 תוצאת ההשוואה המדויקת:")
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                st.markdown(f"""
                <div style="background:#ffffff; border:1px solid #e7e5e4; border-radius:10px; padding:16px; font-size:17.5px; line-height:1.9;">
                    <b style="color:#1e3a8a;">נוסח א' (מחיקות/שינויים באדום):</b><br><br>
                    {" ".join(res_a)}
                </div>
                """, unsafe_allow_html=True)
            with r_col2:
                st.markdown(f"""
                <div style="background:#ffffff; border:1px solid #e7e5e4; border-radius:10px; padding:16px; font-size:17.5px; line-height:1.9;">
                    <b style="color:#166534;">נוסח ב' (הוספות בירוק):</b><br><br>
                    {" ".join(res_b)}
                </div>
                """, unsafe_allow_html=True)

    with tab_gematria:
        st.markdown("##### מחשבון גימטריה קבלי")
        g_col1, g_col2 = st.columns([2, 1])
        with g_col1:
            g_input = st.text_input("הקלד ביטוי או שם קדוש:", placeholder="למשל: אדם קדמון, אהי\"ה, הויה...")
        with g_col2:
            if g_input:
                val = calculate_gematria(fast_clean(g_input))
                st.metric("ערך הגימטריה:", val)

        st.markdown("---")
        st.markdown("##### 🔍 איתור מילים שוות ערך במסד הנתונים")
        target_val = st.number_input("חפש מילים במאגר שערכן שווה ל:", min_value=1, max_value=2000, value=72)
        if st.button("מצא מילים שוות גימטריה"):
            t_gem = time.time()
            cur = conn.cursor()
            cur.execute("SELECT raw_text FROM paragraphs ORDER BY RANDOM() LIMIT 200;")
            sample_paras = cur.fetchall()
            found_words = set()

            for p in sample_paras:
                for w in p[0].split():
                    clean_w = fast_clean(w)
                    if len(clean_w) > 1 and calculate_gematria(clean_w) == target_val:
                        found_words.add(clean_w)
                        if len(found_words) >= 40:
                            break
                if len(found_words) >= 40:
                    break

            el_gem = time.time() - t_gem
            if found_words:
                st.success(f"נמצאו {len(found_words)} מילים שוות גימטריה ל-{target_val} (בתוך {el_gem:.3f} שניות):")
                st.markdown(" · ".join([f"**{w}**" for w in sorted(found_words)]))
            else:
                st.info("לא נמצאו מילים תואמות בטווח הדגימה.")
