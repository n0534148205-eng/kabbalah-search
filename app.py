import difflib
import json
import os
import re
import sqlite3
import time
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="מטמונים",
    page_icon="📜",
    layout="wide",
)

# ----------------- עיצוב ממשק -----------------
st.markdown(
    """
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
        background-color: #f8fafc !important;
        color: #0f172a !important;
        direction: rtl !important;
        text-align: right !important;
    }

    p, span, label, h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] {
        color: #0f172a !important;
        direction: rtl !important;
        text-align: right !important;
    }

    h1, h2, h3 {
        font-family: 'Frank Ruhl Libre', serif !important;
        color: #0284c7 !important;
        font-weight: 700 !important;
    }

    .col-header-box {
        background: #1e3a8a;
        color: #ffffff !important;
        text-align: center;
        padding: 6px;
        font-weight: 800;
        border-radius: 6px;
        font-size: 14px;
        margin-bottom: 8px;
    }

    .or-separator {
        text-align: center;
        color: #64748b;
        font-size: 11px;
        font-weight: 800;
        margin: -8px 0;
    }

    .section-title {
        font-weight: 800;
        color: #1e3a8a;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 4px;
        margin-bottom: 12px;
        font-size: 15px;
    }

    .result-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 18px 22px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03) !important;
    }

    .badge-book {
        display: inline-block;
        background-color: #eff6ff !important;
        color: #1d4ed8 !important;
        font-weight: 800 !important;
        font-size: 13.5px !important;
        padding: 3px 10px !important;
        border-radius: 6px !important;
        border: 1px solid #bfdbfe !important;
        margin-left: 6px !important;
    }

    .badge-section {
        display: inline-block;
        background-color: #fef3c7 !important;
        color: #b45309 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        padding: 3px 10px !important;
        border-radius: 6px !important;
        border: 1px solid #fde68a !important;
        margin-left: 6px !important;
    }

    .snippet-text {
        font-size: 18px !important;
        line-height: 1.95 !important;
        color: #1e293b !important;
        margin-top: 10px !important;
        padding-right: 14px !important;
        border-right: 3px solid #2563eb !important;
        text-align: justify !important;
    }

    .search-highlight {
        background-color: #fde047 !important;
        color: #000000 !important;
        font-weight: 800 !important;
        padding: 1px 4px !important;
        border-radius: 3px;
        border-bottom: 2px solid #ca8a04 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ----------------- JavaScript: מעבר אוטומטי בלחיצה על רווח -----------------
components.html(
    """
<script>
function setupSpaceJump() {
    const doc = window.parent.document;
    for (let col = 1; col <= 4; col++) {
        for (let row = 1; row <= 4; row++) {
            const input = doc.querySelector(`input[aria-label="inp_${col}_${row}"]`);
            if (input && !input.dataset.hasSpaceListener) {
                input.dataset.hasSpaceListener = "true";
                input.addEventListener('keydown', function(e) {
                    if (e.key === ' ' || e.code === 'Space') {
                        if (input.value.trim().length > 0) {
                            e.preventDefault();
                            const nextCol = col < 4 ? col + 1 : 1;
                            const nextInput = doc.querySelector(`input[aria-label="inp_${nextCol}_1"]`);
                            if (nextInput) {
                                nextInput.focus();
                                nextInput.select();
                            }
                        }
                    }
                });
            }
        }
    }
}
setInterval(setupSpaceJump, 400);
</script>
""",
    height=0,
    width=0,
)

DB_FILE = "matmonim_dbs.db"
PARAS_PER_PAGE = 15

if not os.path.exists(DB_FILE):
    st.error(f"⚠️ מסד הנתונים `{DB_FILE}` לא נמצא! הרץ תחילה `python build_index.py`.")
    st.stop()

@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=60.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-32000;")
    conn.execute("PRAGMA mmap_size=67108864;")
    return conn

conn = get_db_connection()

# טעינת נתוני ספרים מה-DB
books_meta_rows = conn.execute("SELECT path, title, category, total_paras, toc_json, author FROM books_meta ORDER BY title").fetchall()
books_by_path = {row[0]: {"title": row[1], "category": row[2], "total": row[3], "toc": row[4], "author": row[5]} for row in books_meta_rows}

# אתחול Session State למאגרים נבחרים (ברירת מחדל: כולם מסומנים)
if "selected_books" not in st.session_state:
    st.session_state["selected_books"] = set(books_by_path.keys())

if "search_history" not in st.session_state:
    st.session_state["search_history"] = []

if "clear_inputs_flag" not in st.session_state:
    st.session_state["clear_inputs_flag"] = False

# ----------------- בניית היררכיית עץ המקורות מתוך תיקיית books -----------------
@st.cache_data
def get_folder_hierarchy():
    hierarchy = {}
    for p, info in books_by_path.items():
        parts = [part.strip() for part in p.split(" / ") if part.strip().lower() != "books"]
        if len(parts) <= 1:
            top = "ספרים כלליים"
            sub = "כללי"
        elif len(parts) == 2:
            top = parts[0]
            sub = "כללי"
        else:
            top = parts[0]
            sub = parts[1]

        if top not in hierarchy:
            hierarchy[top] = {}
        if sub not in hierarchy[top]:
            hierarchy[top][sub] = []
        hierarchy[top][sub].append(p)
    return hierarchy

folder_tree = get_folder_hierarchy()

# ----------------- חלון ניהול המאגרים (עץ מקורות פרויקט השו״ת) -----------------
def render_corpus_manager_content():
    st.markdown("### 🏛️ ניהול המאגרים ועץ המקורות")
    st.caption("סמן ב-V את המאגרים, התיקיות והספרים שבהם יתבצע החיפוש")

    total_books_count = len(books_by_path)
    selected_count = len(st.session_state["selected_books"])

    top_c1, top_c2, top_c3, top_c4 = st.columns([1.2, 1.4, 2.5, 1.2])
    with top_c1:
        if st.button("✅ בחר הכל", use_container_width=True):
            st.session_state["selected_books"] = set(books_by_path.keys())
            st.rerun()
    with top_c2:
        if st.button("❌ התחל שוב (נקה)", use_container_width=True):
            st.session_state["selected_books"] = set()
            st.rerun()
    with top_c3:
        pct = (selected_count / total_books_count * 100) if total_books_count else 0
        st.info(f"נבחרו **{selected_count:,}** מתוך **{total_books_count:,}** ספרים ({pct:.1f}%)")
    with top_c4:
        if st.button("💾 אישור וסגירה", use_container_width=True):
            st.rerun()

    st.markdown("---")

    tab_tree, tab_authors, tab_search = st.tabs(["🌳 עץ מקורות", "✍️ לפי מחברים", "🔍 איתור ספרים מהיר"])

    # טאב 1: עץ מקורות (היררכיית תיקיות מלאה)
    with tab_tree:
        for top_folder, subfolders in folder_tree.items():
            top_all_books = [p for sub_list in subfolders.values() for p in sub_list]
            is_all_selected = all(p in st.session_state["selected_books"] for p in top_all_books)
            is_some_selected = any(p in st.session_state["selected_books"] for p in top_all_books)

            col_chk, col_exp = st.columns([0.08, 0.92])
            with col_chk:
                chk_top = st.checkbox(
                    " ",
                    value=is_all_selected,
                    key=f"chk_top_{top_folder}",
                    label_visibility="collapsed"
                )
                if chk_top != is_all_selected:
                    if chk_top:
                        st.session_state["selected_books"].update(top_all_books)
                    else:
                        st.session_state["selected_books"].difference_update(top_all_books)
                    st.rerun()

            with col_exp:
                with st.expander(f"📕 **{top_folder}** ({len(top_all_books)} ספרים)", expanded=False):
                    for sub_name, b_paths in subfolders.items():
                        if sub_name != "כללי":
                            is_sub_all = all(p in st.session_state["selected_books"] for p in b_paths)
                            sub_c1, sub_c2 = st.columns([0.1, 0.9])
                            with sub_c1:
                                chk_sub = st.checkbox(" ", value=is_sub_all, key=f"chk_sub_{top_folder}_{sub_name}", label_visibility="collapsed")
                                if chk_sub != is_sub_all:
                                    if chk_sub:
                                        st.session_state["selected_books"].update(b_paths)
                                    else:
                                        st.session_state["selected_books"].difference_update(b_paths)
                                    st.rerun()
                            with sub_c2:
                                st.markdown(f"📁 **{sub_name}** ({len(b_paths)} ספרים)")

                        for bp in b_paths:
                            b_title = books_by_path[bp]["title"]
                            is_b_sel = bp in st.session_state["selected_books"]
                            chk_b = st.checkbox(f"📖 {b_title}", value=is_b_sel, key=f"b_{bp}")
                            if chk_b != is_b_sel:
                                if chk_b:
                                    st.session_state["selected_books"].add(bp)
                                else:
                                    st.session_state["selected_books"].discard(bp)
                                st.rerun()

    # טאב 2: לפי מחברים
    with tab_authors:
        authors_map = {}
        for bp, info in books_by_path.items():
            a = info["author"]
            authors_map.setdefault(a, []).append(bp)

        for author_name, a_books in sorted(authors_map.items()):
            is_auth_all = all(p in st.session_state["selected_books"] for p in a_books)
            col_a1, col_a2 = st.columns([0.08, 0.92])
            with col_a1:
                chk_a = st.checkbox(" ", value=is_auth_all, key=f"auth_{author_name}", label_visibility="collapsed")
                if chk_a != is_auth_all:
                    if chk_a:
                        st.session_state["selected_books"].update(a_books)
                    else:
                        st.session_state["selected_books"].difference_update(a_books)
                    st.rerun()
            with col_a2:
                st.markdown(f"✍️ **{author_name}** ({len(a_books)} ספרים)")

    # טאב 3: איתור מהיר
    with tab_search:
        search_filter = st.text_input("הקלד שם ספר לסינון מהיר בעץ:")
        if search_filter:
            matches = [bp for bp in books_by_path.keys() if search_filter in books_by_path[bp]["title"]]
            st.caption(f"נמצאו {len(matches)} ספרים תואמים:")
            for mbp in matches:
                is_mb_sel = mbp in st.session_state["selected_books"]
                chk_mb = st.checkbox(f"{books_by_path[mbp]['title']} [{books_by_path[mbp]['author']}]", value=is_mb_sel, key=f"search_{mbp}")
                if chk_mb != is_mb_sel:
                    if chk_mb:
                        st.session_state["selected_books"].add(mbp)
                    else:
                        st.session_state["selected_books"].discard(mbp)
                    st.rerun()

if hasattr(st, "dialog"):
    @st.dialog("ניהול המאגרים - עץ מקורות", width="large")
    def open_corpus_dialog():
        render_corpus_manager_content()
else:
    def open_corpus_dialog():
        with st.expander("📚 ניהול המאגרים - עץ מקורות", expanded=True):
            render_corpus_manager_content()

# ----------------- הרחבות לשוניות ודקדוקיות -----------------
KABBALAH_ACRONYMS = {
    "אדם קדמון": 'א"ק', "זעיר אנפין": 'ז"א', "אריך אנפין": 'א"א', "עתיק יומין": 'ע"י',
    "אבא ואמא": 'או"א', "ישראל סבא ותבונה": 'ישסו"ת', "עשר ספירות": 'ע"ס',
    "נצח הוד יסוד": 'נה"י', "נצח הוד יסוד מלכות": 'נהי"ם', "חכמה בינה דעת": 'חב"ד',
    "חסד גבורה תפארת": 'חג"ת', "שלוש ראשונות": 'ג"ר', "שבע תחתונות": 'ז"ת',
    "קודשא בריך הוא": 'קוב"ה', "אצילות בריאה יצירה עשיה": 'אבי"ע',
    "אור פנימי": 'או"פ', "אור מקיף": 'או"מ', "אור חוזר": 'או"ח', "אור ישר": 'או"י',
    "אור אינסוף": 'אוא"ס', "מיין נוקבין": 'מ"ן', "מיין דכורין": 'מ"ד',
    "עץ חיים": 'ע"ח', "פרי עץ חיים": 'פע"ח', "שער הכוונות": 'שה"כ',
    "שער הגלגולים": 'שה"ג', "רבי שמעון בר יוחאי": 'רשב"י',
    "רבי משה קורדובירו": 'רמ"ק', "רבי משה חיים לוצאטו": 'רמח"ל',
    "אדוננו רבי יצחק": 'האר"י', "רבי חיים ויטאל": 'מהרח"ו',
}

_strip_chars = {c: None for c in range(0x0591, 0x05C7 + 1)}
for q in ['"', "'", "״", "׳", "`", "”", "“", "’", "‘", "־", "-"]:
    _strip_chars[ord(q)] = None
FAST_CLEAN_TRANS = str.maketrans(_strip_chars)

def fast_clean(text: str) -> str:
    return text.translate(FAST_CLEAN_TRANS)

PREFIX_LIST = [
    "", "ו", "ד", "ש", "ה", "ב", "כ", "ל", "מ",
    "וד", "וש", "וה", "וב", "וכ", "ול", "ומ",
    "שב", "של", "שמ", "שכ", "שה"
]

SUFFIX_LIST = [
    "", "ים", "ות", "ין", "ה", "י", "נו", "ך", "כם", "ם", "ן",
    "יה", "יהם", "יהן", "תא", "א", "יו", "ינו", "יך", "יכם"
]

def expand_hebrew_word(word, opt_pref, opt_suff, opt_aramaic, opt_spelling, opt_quotes, opt_acronyms):
    base = word.strip()
    if not base:
        return []

    if opt_quotes:
        base = fast_clean(base)

    cleaned = fast_clean(base)
    variants = {cleaned}

    if opt_acronyms:
        for full_term, acr in KABBALAH_ACRONYMS.items():
            c_acr = fast_clean(acr)
            c_full = fast_clean(full_term)
            if cleaned == c_acr:
                variants.add(c_full)
            elif cleaned == c_full:
                variants.add(c_acr)

    if opt_aramaic:
        for v in list(variants):
            if v.endswith("ים"):
                variants.add(v[:-2] + "ין")
            elif v.endswith("ין"):
                variants.add(v[:-2] + "ים")
            if v.endswith("ה"):
                variants.add(v[:-1] + "א")
            elif v.endswith("א"):
                variants.add(v[:-1] + "ה")

    if opt_spelling:
        for v in list(variants):
            variants.add(v.replace("ו", ""))
            variants.add(v.replace("י", ""))
            variants.add(v.replace("עלם", "עולם").replace("עלמין", "עולמין"))
            variants.add(v.replace("כהן", "כוהן"))

    final_fts_tokens = []
    for var in variants:
        if " " in var:
            final_fts_tokens.append(f'"{var}"')
            continue

        var_clean = fast_clean(var)
        prefixes = PREFIX_LIST if opt_pref else [""]
        suffixes = SUFFIX_LIST if opt_suff else [""]

        sub_words = []
        for p in prefixes:
            for s in suffixes:
                sub_words.append(f'"{p}{var_clean}{s}"')

        if len(sub_words) > 1:
            final_fts_tokens.append("(" + " OR ".join(sub_words[:40]) + ")")
        elif sub_words:
            final_fts_tokens.append(sub_words[0])

    return final_fts_tokens

SENTENCE_SPLIT_RE = re.compile(r'[\.\:\?\!\;\n]')

def check_proximity_full(raw_text, col_term_groups, scope_type, dist_1_2, dist_2_3, dist_3_4, enforce_order):
    if scope_type == "בתוך מסמך":
        return True

    text_blocks = [raw_text] if scope_type != "בתוך משפט" else [s for s in SENTENCE_SPLIT_RE.split(raw_text) if s.strip()]

    for block in text_blocks:
        tokens = [fast_clean(t) for t in block.split() if t]
        if not tokens:
            continue

        col_pos_lists = []
        possible = True

        for terms in col_term_groups:
            matched_pos = []
            for term in terms:
                target = fast_clean(term.rstrip("*"))
                is_wc = term.endswith("*")
                for idx, tok in enumerate(tokens):
                    if (is_wc and tok.startswith(target)) or (not is_wc and target in tok):
                        matched_pos.append(idx)
            if not matched_pos:
                possible = False
                break
            col_pos_lists.append(sorted(list(set(matched_pos))))

        if not possible:
            continue

        if scope_type in ["בתוך פסקה", "בתוך משפט"]:
            if not enforce_order:
                return True

        import itertools
        for combo in itertools.product(*col_pos_lists):
            if enforce_order and list(combo) != sorted(combo):
                continue

            valid_dist = True
            if scope_type == "טווח מילים":
                pairs = [(0, 1, dist_1_2), (1, 2, dist_2_3), (2, 3, dist_3_4)]
                for i, j, max_d in pairs:
                    if len(combo) > j:
                        if abs(combo[j] - combo[i]) > max_d:
                            valid_dist = False
                            break

            if valid_dist:
                return True

    return False

def highlight_all(text, terms):
    if not terms:
        return text
    clean_terms = sorted(list(set(fast_clean(t.rstrip("*")) for t in terms if len(fast_clean(t)) >= 2)), key=len, reverse=True)
    if not clean_terms:
        return text
    pattern = rf'(?<![א-ת])(?:[ומשכלבהד]{{0,3}})?({"|".join(re.escape(t) for t in clean_terms)})[א-ת]*(?![א-ת])'
    try:
        return re.sub(pattern, r'<span class="search-highlight">\g<0></span>', text)
    except Exception:
        return text

# סרגל צד
with st.sidebar:
    st.markdown("### 📜 מאגר תורני")
    st.markdown(f"**ספרים במאגר:** `{len(books_by_path):,}`")
    num_curr_sel = len(st.session_state["selected_books"])
    st.markdown(f"**ספרים פעילים בחיפוש:** `{num_curr_sel:,}`")
    st.markdown("---")
    st.markdown("#### 🕒 שאילתות קודמות")
    if st.session_state["search_history"]:
        for h_item in reversed(st.session_state["search_history"][-6:]):
            st.caption(f"📌 {h_item}")
    else:
        st.caption("אין שאילתות קודמות.")

# כותרת ראשית
st.markdown("# 💎 מַטְמוֹנִים · חיפוש טבלאי פרויקט השו״ת")

# בר ניהול מאגרים ובחירת ספרים
bar_c1, bar_c2, bar_c3 = st.columns([1.6, 2.5, 0.8])
with bar_c1:
    if st.button("📚 המאגרים המשתתפים (עץ מקורות)", use_container_width=True):
        open_corpus_dialog()

with bar_c2:
    sel_count = len(st.session_state["selected_books"])
    tot_count = len(books_by_path)
    if sel_count == tot_count:
        st.success(f"חיפוש פעיל ב**כל המאגרים** ({tot_count:,} ספרים)")
    elif sel_count == 0:
        st.error("⚠️ לא נבחרו מאגרים! לחץ על הכפתור ובחר לפחות מאגר אחד.")
    else:
        st.warning(f"חיפוש ממוקד ב-**{sel_count:,}** מתוך {tot_count:,} ספרים שנבחרו בעץ המקורות")

with bar_c3:
    if st.button("🧹 ניקוי הכל", use_container_width=True):
        st.session_state["clear_inputs_flag"] = not st.session_state["clear_inputs_flag"]
        st.rerun()

clear_salt = "1" if st.session_state["clear_inputs_flag"] else "0"

with st.form("reshut_search_form"):
    st.markdown("<div class='section-title'>מרכיבי החיפוש (טורים: 'וגם' | שורות: 'או' | רווח: מעבר לטור הבא)</div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    # --- טור 1 ---
    with c1:
        st.markdown("<div class='col-header-box'>[טור 1] מרכיב 1</div>", unsafe_allow_html=True)
        w1_1 = st.text_input("inp_1_1", key=f"w1_1_{clear_salt}", placeholder="מילה / ביטוי", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w1_2 = st.text_input("inp_1_2", key=f"w1_2_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w1_3 = st.text_input("inp_1_3", key=f"w1_3_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w1_4 = st.text_input("inp_1_4", key=f"w1_4_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")

        with st.popover("⚙️ מאפייני מרכיב 1", use_container_width=True):
            c1_pref = st.checkbox("ק/ד קידומות (ומשכלב\"ד)", value=True, key="c1_p")
            c1_suff = st.checkbox("ס/מ סיומות (ים, ות, נו...)", value=False, key="c1_s")
            c1_spelling = st.checkbox("ח כתיב מלא/חסר (אהו\"י)", value=True, key="c1_h")
            c1_aramaic = st.checkbox("ל סיומות ארמית (ין ↔ ים)", value=True, key="c1_l")
            c1_quotes = st.checkbox("ג עם/בלי גרשיים", value=True, key="c1_g")
            c1_acronyms = st.checkbox("כולל ראשי תיבות", value=True, key="c1_rt")
            c1_not = st.checkbox("🚫 שלילת מרכיב זה (NOT)", value=False, key="c1_not")

    # --- טור 2 ---
    with c2:
        st.markdown("<div class='col-header-box'>וגם ➔ [טור 2] מרכיב 2</div>", unsafe_allow_html=True)
        w2_1 = st.text_input("inp_2_1", key=f"w2_1_{clear_salt}", placeholder="מילה / ביטוי", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w2_2 = st.text_input("inp_2_2", key=f"w2_2_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w2_3 = st.text_input("inp_2_3", key=f"w2_3_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w2_4 = st.text_input("inp_2_4", key=f"w2_4_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")

        with st.popover("⚙️ מאפייני מרכיב 2", use_container_width=True):
            c2_pref = st.checkbox("ק/ד קידומות (ומשכלב\"ד)", value=True, key="c2_p")
            c2_suff = st.checkbox("ס/מ סיומות (ים, ות, נו...)", value=False, key="c2_s")
            c2_spelling = st.checkbox("ח כתיב מלא/חסר (אהו\"י)", value=True, key="c2_h")
            c2_aramaic = st.checkbox("ל סיומות ארמית (ין ↔ ים)", value=True, key="c2_l")
            c2_quotes = st.checkbox("ג עם/בלי גרשיים", value=True, key="c2_g")
            c2_acronyms = st.checkbox("כולל ראשי תיבות", value=True, key="c2_rt")
            c2_not = st.checkbox("🚫 שלילת מרכיב זה (NOT)", value=False, key="c2_not")

    # --- טור 3 ---
    with c3:
        st.markdown("<div class='col-header-box'>וגם ➔ [טור 3] מרכיב 3</div>", unsafe_allow_html=True)
        w3_1 = st.text_input("inp_3_1", key=f"w3_1_{clear_salt}", placeholder="(אופציונלי)", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w3_2 = st.text_input("inp_3_2", key=f"w3_2_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w3_3 = st.text_input("inp_3_3", key=f"w3_3_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w3_4 = st.text_input("inp_3_4", key=f"w3_4_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")

        with st.popover("⚙️ מאפייני מרכיב 3", use_container_width=True):
            c3_pref = st.checkbox("ק/ד קידומות (ומשכלב\"ד)", value=True, key="c3_p")
            c3_suff = st.checkbox("ס/מ סיומות (ים, ות, נו...)", value=False, key="c3_s")
            c3_spelling = st.checkbox("ח כתיב מלא/חסר (אהו\"י)", value=True, key="c3_h")
            c3_aramaic = st.checkbox("ל סיומות ארמית (ין ↔ ים)", value=True, key="c3_l")
            c3_quotes = st.checkbox("ג עם/בלי גרשיים", value=True, key="c3_g")
            c3_acronyms = st.checkbox("כולל ראשי תיבות", value=True, key="c3_rt")
            c3_not = st.checkbox("🚫 שלילת מרכיב זה (NOT)", value=False, key="c3_not")

    # --- טור 4 ---
    with c4:
        st.markdown("<div class='col-header-box'>וגם ➔ [טור 4] מרכיב 4</div>", unsafe_allow_html=True)
        w4_1 = st.text_input("inp_4_1", key=f"w4_1_{clear_salt}", placeholder="(אופציונלי)", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w4_2 = st.text_input("inp_4_2", key=f"w4_2_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w4_3 = st.text_input("inp_4_3", key=f"w4_3_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")
        st.markdown("<div class='or-separator'>או</div>", unsafe_allow_html=True)
        w4_4 = st.text_input("inp_4_4", key=f"w4_4_{clear_salt}", placeholder="מילה חלופית", label_visibility="collapsed")

        with st.popover("⚙️ מאפייני מרכיב 4", use_container_width=True):
            c4_pref = st.checkbox("ק/ד קידומות (ומשכלב\"ד)", value=True, key="c4_p")
            c4_suff = st.checkbox("ס/מ סיומות (ים, ות, נו...)", value=False, key="c4_s")
            c4_spelling = st.checkbox("ח כתיב מלא/חסר (אהו\"י)", value=True, key="c4_h")
            c4_aramaic = st.checkbox("ל סיומות ארמית (ין ↔ ים)", value=True, key="c4_l")
            c4_quotes = st.checkbox("ג עם/בלי גרשיים", value=True, key="c4_g")
            c4_acronyms = st.checkbox("כולל ראשי תיבות", value=True, key="c4_rt")
            c4_not = st.checkbox("🚫 שלילת מרכיב זה (NOT)", value=False, key="c4_not")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # ---------------- 2. מרחקים ----------------
    st.markdown("<div class='section-title'>מרחקים ותחום החיפוש</div>", unsafe_allow_html=True)
    m_row1, m_row2 = st.columns([2, 3])
    with m_row1:
        scope_choice = st.radio("תחום החיפוש:", ["בתוך פסקה", "טווח מילים", "בתוך משפט", "בתוך מסמך"], horizontal=True, index=0)
    with m_row2:
        dist_cols = st.columns(3)
        with dist_cols[0]:
            dist_1_2 = st.number_input("בין טור 1 ל-2:", min_value=1, max_value=150, value=10, disabled=(scope_choice != "טווח מילים"))
        with dist_cols[1]:
            dist_2_3 = st.number_input("בין טור 2 ל-3:", min_value=1, max_value=150, value=10, disabled=(scope_choice != "טווח מילים"))
        with dist_cols[2]:
            dist_3_4 = st.number_input("בין טור 3 ל-4:", min_value=1, max_value=150, value=10, disabled=(scope_choice != "טווח מילים"))

    rc1, rc2 = st.columns([2, 1])
    with rc1:
        enforce_order = st.checkbox("שמור על סדר המרכיבים (טור 1 ואז טור 2 וכו')", value=False)
    with rc2:
        limit_sel = st.selectbox("מגבלת תוצאות:", ["500", "1,000", "2,000", "5,000", "ללא הגבלה"], index=1)

    submitted = st.form_submit_button("⚡ בצע חיפוש (FTS)", use_container_width=True)

cols_config = [
    {
        "words": [w.strip() for w in [w1_1, w1_2, w1_3, w1_4] if w.strip()],
        "pref": c1_pref, "suff": c1_suff, "spell": c1_spelling, "aram": c1_aramaic, "quot": c1_quotes, "acr": c1_acronyms, "not": c1_not
    },
    {
        "words": [w.strip() for w in [w2_1, w2_2, w2_3, w2_4] if w.strip()],
        "pref": c2_pref, "suff": c2_suff, "spell": c2_spelling, "aram": c2_aramaic, "quot": c2_quotes, "acr": c2_acronyms, "not": c2_not
    },
    {
        "words": [w.strip() for w in [w3_1, w3_2, w3_3, w3_4] if w.strip()],
        "pref": c3_pref, "suff": c3_suff, "spell": c3_spelling, "aram": c3_aramaic, "quot": c3_quotes, "acr": c3_acronyms, "not": c3_not
    },
    {
        "words": [w.strip() for w in [w4_1, w4_2, w4_3, w4_4] if w.strip()],
        "pref": c4_pref, "suff": c4_suff, "spell": c4_spelling, "aram": c4_aramaic, "quot": c4_quotes, "acr": c4_acronyms, "not": c4_not
    },
]

active_cols_cfg = [c for c in cols_config if len(c["words"]) > 0]

if submitted:
    selected_set = st.session_state["selected_books"]
    if not selected_set:
        st.error("⚠️ לא נבחרו מאגרים בעץ המקורות! לחץ על 'המאגרים המשתתפים' וסמן לפחות מאגר אחד.")
    elif not active_cols_cfg:
        st.warning("נא להזין לפחות מילה אחת באחד הטורים.")
    else:
        t_start = time.time()
        
        history_desc = " + ".join(["/".join(c["words"]) for c in active_cols_cfg])
        if history_desc not in st.session_state["search_history"]:
            st.session_state["search_history"].append(history_desc)

        col_fts_clauses = []
        all_terms_flat = []
        positive_cols_words = []

        for col_cfg in active_cols_cfg:
            col_tokens = []
            for word in col_cfg["words"]:
                all_terms_flat.append(word)
                expanded = expand_hebrew_word(
                    word,
                    col_cfg["pref"],
                    col_cfg["suff"],
                    col_cfg["aram"],
                    col_cfg["spell"],
                    col_cfg["quot"],
                    col_cfg["acr"]
                )
                if expanded:
                    col_tokens.extend(expanded)

            if col_tokens:
                sub_clause = "(" + " OR ".join(col_tokens) + ")"
                if col_cfg["not"]:
                    col_fts_clauses.append(f"NOT {sub_clause}")
                else:
                    col_fts_clauses.append(sub_clause)
                    positive_cols_words.append(col_cfg["words"])

        fts_query = " AND ".join(col_fts_clauses)
        limit_map = {"500": 500, "1,000": 1000, "2,000": 2000, "5,000": 5000, "ללא הגבלה": 50000}
        max_rows = limit_map.get(limit_sel, 1000)

        sql = """
        SELECT p.book_path, b.title, b.author, b.category, b.total_paras, p.sec_name, p.p_num, p.raw_text
        FROM dbs_index d
        JOIN paragraphs p ON d.rowid = p.id
        JOIN books_meta b ON p.book_path = b.path
        WHERE d.clean_text MATCH ?
        """
        params = [fts_query]

        is_partial_selection = len(selected_set) < len(books_by_path)
        if is_partial_selection and len(selected_set) <= 500:
            sql += f" AND p.book_path IN ({','.join(['?']*len(selected_set))})"
            params.extend(list(selected_set))

        sql += " LIMIT ?;"
        params.append(max_rows)

        results = []
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            hits = cur.fetchall()

            for h in hits:
                b_path = h[0]
                if is_partial_selection and b_path not in selected_set:
                    continue

                raw_text = h[7]
                if not check_proximity_full(raw_text, positive_cols_words, scope_choice, dist_1_2, dist_2_3, dist_3_4, enforce_order):
                    continue

                results.append({
                    "book_path": b_path,
                    "title": h[1],
                    "author": h[2],
                    "category": h[3],
                    "total_p": h[4],
                    "section": h[5],
                    "p_num": h[6],
                    "raw_text": raw_text,
                })
        except sqlite3.OperationalError as e:
            st.error(f"שגיאת תחביר בחיפוש: {e}")

        elapsed = time.time() - t_start
        st.session_state["results"] = results
        st.session_state["terms"] = all_terms_flat
        st.session_state["elapsed"] = elapsed

if "results" in st.session_state:
    res = st.session_state["results"]
    terms = st.session_state.get("terms", [])
    elapsed = st.session_state.get("elapsed", 0.0)

    st.markdown(f"#### 🔍 נמצאו `{len(res)}` תוצאות מדויקות בתוך `{elapsed:.3f}` שניות")

    if res:
        PAGE_SIZE = 25
        total_pages = max(1, (len(res) + PAGE_SIZE - 1) // PAGE_SIZE)
        p_c1, _ = st.columns([1, 4])
        with p_c1:
            cur_p = st.number_input(f"עמוד (מתוך {total_pages}):", 1, total_pages, 1)

        start = (cur_p - 1) * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(res))

        for idx, r in enumerate(res[start:end]):
            snippet = highlight_all(r["raw_text"], terms)
            st.markdown(
                f"""
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div>
                            <span class="badge-book">📖 {r['title']}</span>
                            <span class="badge-section">📍 {r['section']}</span>
                            <span style="font-size: 13px; color: #64748b; font-weight: 600;">מחבר: {r['author']} · מדור: {r['category']}</span>
                        </div>
                        <span style="font-size: 13px; color: #94a3b8; font-weight: 700;">פסקה {r['p_num']} מתוך {r['total_p']}</span>
                    </div>
                    <div class="snippet-text">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            b1, _ = st.columns([1.5, 4])
            with b1:
                with st.popover("📋 העתק ציטוט"):
                    citation = f'[{r["title"]}, {r["section"]}]: "{r["raw_text"].strip()}"'
                    st.text_area("ציטוט להערת שוליים:", citation, height=90)
            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
