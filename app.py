import streamlit as st
import os
import re
import zipfile

st.set_page_config(
    page_title="אוצר ספרי קבלה | מנוע חיפוש ועיון",
    page_icon="📖",
    layout="wide"
)

# --- אכיפת מראה בהיר ונקי (מונע שחור על שחור ופותר ניגודיות בכל הרכיבים) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700;800&family=Frank+Ruhl+Libre:wght@600;700&display=swap');

    /* 1. רקע כללי של האפליקציה */
    html, body, .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stHeader"] {
        font-family: 'Assistant', sans-serif !important;
        background-color: #f6f5f0 !important;
        color: #1c1917 !important;
        direction: rtl !important;
        text-align: right !important;
    }

    /* 2. אכיפת צבע טקסט ברור כברירת מחדל */
    p, span, label, h1, h2, h3, h4, h5, h6, [data-testid="stMarkdownContainer"] {
        color: #1c1917 !important;
        direction: rtl !important;
        text-align: right !important;
    }

    /* 3. כותרות */
    h1, h2, h3 {
        font-family: 'Frank Ruhl Libre', serif !important;
        color: #0c0a09 !important;
        font-weight: 700 !important;
    }

    /* 4. תיבות טופס וחיפוש */
    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e7e5e4 !important;
        border-radius: 14px !important;
        padding: 22px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }

    /* 5. תיבות קלט (Input) */
    .stTextInput input, .stNumberInput input, textarea {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        border: 1.5px solid #d6d3d1 !important;
        border-radius: 10px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }

    /* 6. פתרון מוחלט לרשימות נפתחות (Popovers & Dropdown Menus) */
    div[data-baseweb="select"], 
    div[data-baseweb="select"] * {
        background-color: #ffffff !important;
        color: #1c1917 !important;
    }

    div[data-baseweb="popover"], 
    div[data-baseweb="popover"] *,
    div[data-baseweb="menu"], 
    div[data-baseweb="menu"] *,
    ul[role="listbox"], 
    ul[role="listbox"] *,
    li[role="option"], 
    li[role="option"] * {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        font-weight: 600 !important;
    }

    li[role="option"]:hover, 
    li[role="option"]:hover * {
        background-color: #eff6ff !important;
        color: #1d4ed8 !important;
    }

    /* 7. לשוניות מתקפלות (Expanders) - רקע בהיר מובטח */
    [data-testid="stExpander"], details {
        background-color: #ffffff !important;
        border: 1px solid #e7e5e4 !important;
        border-radius: 10px !important;
    }
    summary, summary * {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        font-weight: 700 !important;
    }
    summary:hover {
        background-color: #f5f5f4 !important;
    }
    [data-testid="stExpander"] div {
        background-color: #ffffff !important;
    }

    /* 8. כרטיסיית תוצאה צפה */
    .result-card {
        background: #ffffff !important;
        border: 1px solid #e7e5e4 !important;
        border-radius: 14px !important;
        padding: 20px 24px !important;
        margin-bottom: 18px !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03) !important;
    }

    .badge-book {
        display: inline-block;
        background-color: #eff6ff !important;
        color: #1e40af !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        padding: 4px 12px !important;
        border-radius: 16px !important;
        border: 1px solid #dbeafe !important;
        margin-left: 8px !important;
    }
    .badge-location {
        display: inline-block;
        background-color: #f5f5f4 !important;
        color: #57534e !important;
        font-size: 13px !important;
        padding: 4px 10px !important;
        border-radius: 16px !important;
    }

    .snippet-text {
        font-size: 17.5px !important;
        line-height: 1.85 !important;
        color: #292524 !important;
        margin-top: 12px !important;
        padding-right: 14px !important;
        border-right: 3px solid #3b82f6 !important;
        text-align: justify !important;
    }

    .search-highlight {
        background-color: #fde047 !important;
        color: #000000 !important;
        font-weight: 800 !important;
        padding: 2px 5px !important;
        border-radius: 4px !important;
        border-bottom: 1.5px solid #ca8a04 !important;
    }

    /* 9. כפתורים */
    .stButton button {
        background-color: #ffffff !important;
        color: #1c1917 !important;
        border: 1.5px solid #d6d3d1 !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    .stButton button:hover {
        background-color: #f5f5f4 !important;
        border-color: #a8a29e !important;
    }

    div[data-testid="stForm"] .stButton button {
        background-color: #1e3a8a !important;
        color: #ffffff !important;
        border: none !important;
    }
    div[data-testid="stForm"] .stButton button * {
        color: #ffffff !important;
    }
    div[data-testid="stForm"] .stButton button:hover {
        background-color: #1d4ed8 !important;
    }

    /* 10. סרגל צד (Sidebar) */
    [data-testid="stSidebar"], 
    [data-testid="stSidebarContent"] {
        background-color: #f1efea !important;
        border-left: 1px solid #e7e5e4 !important;
    }
    [data-testid="stSidebar"] * {
        color: #1c1917 !important;
    }
    [data-testid="stSidebar"] .stButton button {
        background-color: #ffffff !important;
    }

    /* מתג בחירת מצב */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        background-color: #e7e5e4 !important;
        padding: 4px;
        border-radius: 12px;
    }
    div[data-testid="stRadio"] label span {
        color: #1c1917 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

BOOKS_FOLDER = "books"
if not os.path.exists(BOOKS_FOLDER):
    os.makedirs(BOOKS_FOLDER)

if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "🔍 חיפוש במאגר"
if "reader_book_key" not in st.session_state:
    st.session_state["reader_book_key"] = None
if "reader_target_p" not in st.session_state:
    st.session_state["reader_target_p"] = 1
if "reader_page" not in st.session_state:
    st.session_state["reader_page"] = 1

DEFAULT_ACRONYMS = {
    "אדם קדמון": "א\"ק",
    "זעיר אנפין": "ז\"א",
    "אריך אנפין": "א\"א",
    "אבא ואמא": "או\"א",
    "עשר ספירות": "ע\"ס",
    "נצח הוד יסוד": "נה\"י",
    "חכמה בינה דעת": "חב\"ד",
    "חסד גבורה תפארת": "חג\"ת",
    "שלוש ראשונות": "ג\"ר",
    "שלש ראשונות": "ג\"ר",
    "שבע תחתונות": "ז\"ת",
    "קודשא בריך הוא": "קוב\"ה",
    "אצילות בריאה יצירה עשיה": "אבי\"ע",
    "בריאה יצירה עשיה": "בי\"ע",
    "עץ חיים": "ע\"ח",
    "מיין נוקבין": "מ\"ן",
    "מיין דכורין": "מ\"ד",
    "עולם הזה": "עוה\"ז",
    "עולם הבא": "עוה\"ב",
    "בעל שם טוב": "בעש\"ט",
    "רבי שמעון בר יוחאי": "רשב\"י",
    "רבי משה קורדובירו": "רמ\"ק",
    "רבי משה חיים לוצאטו": "רמח\"ל",
    "אדוננו רבי יצחק": "האר\"י",
}

def remove_niqqud(text):
    return re.sub(r'[\u0591-\u05BD\u05BF-\u05C2\u05C4-\u05C7]', '', text)

def clean_quotes(text):
    return text.replace('"', '').replace("'", "").replace('״', '').replace('׳', '')

def clean_file_extension(name):
    if name.lower().endswith(".txt"):
        name = name[:-4]
    return name.strip()

def extract_title_and_clean_text(raw_content, file_path):
    title = None
    title_match = re.search(r'<title>(.*?)</title>', raw_content[:3000], re.IGNORECASE)
    if title_match:
        t_clean = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        if t_clean and any('\u0590' <= c <= '\u05FF' for c in t_clean):
            title = clean_file_extension(t_clean)

    content_nl = re.sub(r'<(?:br|p|div|d|h[1-6]|hr)[^>]*>', '\n\n', raw_content, flags=re.IGNORECASE)
    clean_content = re.sub(r'<[^>]+>', '', content_nl)
    clean_content = re.sub(r'[ \t]+', ' ', clean_content)
    clean_content = re.sub(r'\n{3,}', '\n\n', clean_content)

    if not title:
        lines = [line.strip() for line in clean_content.split('\n') if line.strip()][:10]
        for line in lines:
            if any('\u0590' <= c <= '\u05FF' for c in line) and len(line) <= 70:
                title = clean_file_extension(line)
                break

    if not title:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        title = clean_file_extension(base_name)

    return title, clean_content

@st.cache_data
def load_all_books():
    books = {}
    for root, dirs, files in os.walk(BOOKS_FOLDER):
        for filename in files:
            if filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                raw_rel_path = os.path.relpath(filepath, BOOKS_FOLDER)
                clean_path = os.path.splitext(raw_rel_path)[0].replace("\\", " / ")

                raw_content = ""
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                except UnicodeDecodeError:
                    with open(filepath, 'r', encoding='cp1255', errors='ignore') as f:
                        raw_content = f.read()

                book_title, clean_content = extract_title_and_clean_text(raw_content, filepath)

                raw_paras = [p.strip() for p in clean_content.split("\n\n") if p.strip()]
                paras = []
                for p in raw_paras:
                    if len(p) > 1500:
                        sentences = p.split(". ")
                        cur_p = ""
                        for s in sentences:
                            cur_p += s + ". "
                            if len(cur_p) > 800:
                                paras.append(cur_p.strip())
                                cur_p = ""
                        if cur_p:
                            paras.append(cur_p.strip())
                    else:
                        paras.append(p)

                books[clean_path] = {
                    "title": book_title,
                    "path": clean_path,
                    "content": clean_content,
                    "paragraphs": paras
                }
    return books

def make_flexible_spelling(word):
    if len(word) < 2:
        return re.escape(word)
    first = word[0]
    middle = word[1:-1]
    last = word[-1]
    parts = [re.escape(first), "[וי]{0,2}"]
    for ch in middle:
        if ch in 'וי':
            continue
        parts.append(re.escape(ch))
        parts.append("[וי]{0,2}")
    if last in 'אה':
        parts.append("[אה]")
    else:
        parts.append(re.escape(last))
    return "".join(parts)

def make_acronym_pattern(acr):
    clean = clean_quotes(acr)
    if len(clean) < 2:
        return rf"{re.escape(clean)}['׳״\"]"
    all_but_last = clean[:-1]
    last = clean[-1]
    prefix_part = r'["\'״׳]?'.join([re.escape(ch) for ch in all_but_last])
    return rf'{prefix_part}["\'״׳]+{re.escape(last)}'

def get_synonyms(term, acronym_map):
    clean_term = clean_quotes(term.strip())
    results = [term.strip()]
    for full_form, acr in acronym_map.items():
        if clean_term == clean_quotes(acr):
            results.append(full_form)
        elif clean_term == clean_quotes(full_form):
            results.append(acr)
    return list(set(results))

def get_term_pattern(term, allow_prefixes=True, allow_flexible=True, allow_acronyms=True, acronym_map=None):
    if acronym_map is None:
        acronym_map = {}
    variants = get_synonyms(term, acronym_map) if allow_acronyms else [term]
    variant_patterns = []
    
    for v in variants:
        if any(q in v for q in ['"', "'", '״', '׳']) or (len(v) <= 4 and ' ' not in v and v in [clean_quotes(a) for a in acronym_map.values()]):
            p = make_acronym_pattern(v)
        elif ' ' in v:
            words = v.split()
            word_pats = []
            for w in words:
                bw = make_flexible_spelling(w) if allow_flexible else re.escape(w)
                word_pats.append(rf'(?:[ומשכלבה]{{1,3}})?{bw}' if allow_prefixes else bw)
            p = r'\s+'.join(word_pats)
        else:
            p = make_flexible_spelling(v) if allow_flexible else re.escape(v)
        variant_patterns.append(p)
        
    combined = "|".join(variant_patterns)
    return rf'(?<![א-ת])(?:[ומשכלבה]{{1,3}})?(?:{combined})(?![א-ת])' if allow_prefixes else rf'(?<![א-ת])(?:{combined})(?![א-ת])'

def highlight_matches(text, patterns):
    if not patterns:
        return text
    combined_pattern = "(" + "|".join(patterns) + ")"
    return re.sub(
        combined_pattern, 
        r'<span class="search-highlight">\g<0></span>', 
        text
    )

def get_sort_key(title):
    t = title.strip()
    if t.startswith("ספר "):
        t = t[4:].strip()
    return t

# --- תפריט צד ---
with st.sidebar:
    st.markdown("### 📚 מאגר הספרים")
    books_data = load_all_books()
    st.markdown(f"**ספרים טעונים במערכת:** `{len(books_data)}`")

    if st.button("🔄 רענון מאגר", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown("#### 📥 הוספת ספרים")
    uploaded_files = st.file_uploader("העלאת קובצי TXT או תיקיית ZIP:", type=["txt", "zip"], accept_multiple_files=True)
    if uploaded_files:
        added_count = 0
        for uploaded_file in uploaded_files:
            if uploaded_file.name.endswith(".zip"):
                with zipfile.ZipFile(uploaded_file, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".txt") and not filename.startswith("__MACOSX"):
                            z.extract(filename, BOOKS_FOLDER)
                            added_count += 1
            elif uploaded_file.name.endswith(".txt"):
                file_path = os.path.join(BOOKS_FOLDER, uploaded_file.name)
                if not os.path.exists(file_path):
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    added_count += 1
        if added_count > 0:
            st.cache_data.clear()
            st.success(f"נוספו בהצלחה {added_count} ספרים!")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 🏷️ מילון קיצורים")
    with st.expander("הוספת קיצורים אישיים"):
        st.caption("פורמט: ביטוי מלא = קיצור")
        custom_acr_text = st.text_area("קיצורים:", height=80)

acronym_dict = DEFAULT_ACRONYMS.copy()
if custom_acr_text:
    for line in custom_acr_text.strip().split("\n"):
        if "=" in line:
            full, acr = line.split("=", 1)
            acronym_dict[full.strip()] = acr.strip()

sorted_book_keys = sorted(
    books_data.keys(),
    key=lambda k: get_sort_key(books_data[k]['title'])
)

# --- כותרת ומעבר מצבים ---
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown("# 📖 אוצר חכמת הקבלה")
    st.caption("מנוע חיפוש, מחקר ועיון מתקדם בספרי קבלה וחסידות")

with header_col2:
    mode_choice = st.radio(
        "מצב עבודה:",
        ["🔍 חיפוש במאגר", "📖 בית מדרש לעיון"],
        horizontal=True,
        index=0 if st.session_state["app_mode"] == "🔍 חיפוש במאגר" else 1,
        label_visibility="collapsed"
    )
    st.session_state["app_mode"] = mode_choice

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# ==========================================
# מצב 1: חיפוש במאגר
# ==========================================
if st.session_state["app_mode"] == "🔍 חיפוש במאגר":
    selected_search_book = st.selectbox(
        "סינון לפי ספר ספציפי (אופציונלי):",
        options=sorted_book_keys,
        index=None,
        placeholder="🔍 הקלד שם ספר לסינון (למשל: זוהר, עץ חיים)... או השאר ריק לחיפוש בכל המאגר",
        format_func=lambda k: f"{books_data[k]['title']}  ·  [{books_data[k]['path']}]"
    )

    with st.form("search_form"):
        col_q, col_mode = st.columns([5, 3])
        with col_q:
            query = st.text_input("שאילתת חיפוש:", placeholder="הקלד מושג או מילים (למשל: אור אינסוף, עשר ספירות, א\"ק)...", label_visibility="collapsed")
            c1, c2, c3 = st.columns(3)
            with c1:
                allow_prefixes = st.checkbox("אותיות שימוש (מש״ה וכֿל״ב)", value=True)
            with c2:
                allow_flexible = st.checkbox("כתיב מלא וחסר", value=True)
            with c3:
                allow_acronyms = st.checkbox("פענוח ראשי תיבות", value=True)

        with col_mode:
            search_mode = st.radio("אופן החיפוש:", ["ביטוי מדויק", "כל המילים (וגם)", "לפחות אחת (או)", "מרחק בין מילים"], horizontal=True)
            max_distance = st.slider("מרחק מילים מקסימלי:", 1, 30, 7)

        submitted = st.form_submit_button("🔍 מצא מקורות במאגר", use_container_width=True)

    if query and (submitted or "last_query" in st.session_state):
        st.session_state["last_query"] = query
        clean_query = remove_niqqud(query.strip())
        words = [w for w in clean_query.split() if w]
        results = []

        books_to_search = {selected_search_book: books_data[selected_search_book]} if selected_search_book else books_data

        patterns_to_check = [get_term_pattern(w, allow_prefixes, allow_flexible, allow_acronyms, acronym_dict) for w in words]
        proximity_pattern = None
        if search_mode == "מרחק בין מילים" and len(words) >= 2:
            p1, p2 = patterns_to_check[0], patterns_to_check[1]
            dist_regex = rf'(?:\s+\S+){{0,{max_distance}}}\s+'
            proximity_pattern = rf'(?:(?:{p1}{dist_regex}{p2})|(?:{p2}{dist_regex}{p1}))'

        with st.spinner("סורק את כל דפי המאגר..."):
            for book_key, book_info in books_to_search.items():
                paragraphs = book_info["paragraphs"]
                total_p = len(paragraphs)

                for p_idx, para in enumerate(paragraphs):
                    para_clean = remove_niqqud(para)
                    match_found = False
                    matched_patterns = []

                    if search_mode == "ביטוי מדויק":
                        exact_pat = get_term_pattern(clean_query, allow_prefixes, allow_flexible, allow_acronyms, acronym_dict)
                        if re.search(exact_pat, para_clean):
                            match_found = True
                            matched_patterns = [exact_pat]
                    elif search_mode == "כל המילים (וגם)":
                        if all(re.search(pat, para_clean) for pat in patterns_to_check):
                            match_found = True
                            matched_patterns = patterns_to_check
                    elif search_mode == "לפחות אחת (או)":
                        matched = [pat for pat in patterns_to_check if re.search(pat, para_clean)]
                        if matched:
                            match_found = True
                            matched_patterns = matched
                    elif search_mode == "מרחק בין מילים":
                        if proximity_pattern and re.search(proximity_pattern, para_clean):
                            match_found = True
                            matched_patterns = patterns_to_check[:2]

                    if match_found:
                        snippet = highlight_matches(para_clean, matched_patterns)
                        prev_p = [remove_niqqud(p) for p in paragraphs[max(0, p_idx - 1) : p_idx] if p.strip()]
                        next_p = [remove_niqqud(p) for p in paragraphs[p_idx + 1 : min(total_p, p_idx + 2)] if p.strip()]

                        results.append({
                            "book_key": book_key,
                            "title": book_info["title"],
                            "path": book_info["path"],
                            "snippet": snippet,
                            "prev_context": prev_p,
                            "next_context": next_p,
                            "p_num": p_idx + 1,
                            "total_p": total_p
                        })

        PAGE_SIZE = 20
        total_results = len(results)
        
        st.markdown(f"#### נמצאו `{total_results}` תוצאות עבור **\"{query}\"**")

        if total_results > 0:
            total_pages = max(1, (total_results + PAGE_SIZE - 1) // PAGE_SIZE)
            
            p_col1, p_col2 = st.columns([1, 4])
            with p_col1:
                current_page = st.number_input(f"עמוד (מתוך {total_pages}):", 1, total_pages, 1)
            
            start_idx = (current_page - 1) * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, total_results)

            for idx, r in enumerate(results[start_idx:end_idx]):
                st.markdown(f"""
                <div class="result-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span class="badge-book">📖 {r['title']}</span>
                            <span class="badge-location">פסקה {r['p_num']} מתוך {r['total_p']}</span>
                        </div>
                        <span style="font-size: 13px; color: #78716c; font-weight: 600;">{r['path']}</span>
                    </div>
                    <div class="snippet-text">
                        {r['snippet']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                btn_col1, btn_col2 = st.columns([1, 4])
                with btn_col1:
                    if st.button("📖 פתח לעיון מלא", key=f"open_reader_{start_idx + idx}", use_container_width=True):
                        st.session_state["app_mode"] = "📖 בית מדרש לעיון"
                        st.session_state["reader_book_key"] = r["book_key"]
                        st.session_state["reader_target_p"] = r["p_num"]
                        st.rerun()

                with btn_col2:
                    with st.expander("🔍 הצג הקשר מורחב (לפני ואחרי)"):
                        if r['prev_context']:
                            for p_text in r['prev_context']:
                                st.markdown(f"<p style='color: #44403c; font-size: 15.5px; line-height: 1.7;'>{p_text}</p>", unsafe_allow_html=True)
                        st.markdown(f"<div style='background-color: #fefce8; border-right: 4px solid #eab308; padding: 12px; border-radius: 6px; margin: 8px 0;'>{r['snippet']}</div>", unsafe_allow_html=True)
                        if r['next_context']:
                            for p_text in r['next_context']:
                                st.markdown(f"<p style='color: #44403c; font-size: 15.5px; line-height: 1.7;'>{p_text}</p>", unsafe_allow_html=True)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# ==========================================
# מצב 2: בית מדרש לעיון (Reader)
# ==========================================
else:
    if not books_data:
        st.warning("אין עדיין ספרים במאגר.")
    else:
        top_col1, top_col2 = st.columns([3, 1])

        default_reader_idx = 0
        if st.session_state["reader_book_key"] in sorted_book_keys:
            default_reader_idx = sorted_book_keys.index(st.session_state["reader_book_key"])

        with top_col1:
            selected_reader_key = st.selectbox(
                "ספר נוכחי:",
                options=sorted_book_keys,
                index=default_reader_idx,
                format_func=lambda k: f"{books_data[k]['title']}  ·  [{books_data[k]['path']}]"
            )
            st.session_state["reader_book_key"] = selected_reader_key

        with top_col2:
            font_size = st.slider("גודל כתב:", 15, 34, 20)

        current_book = books_data[selected_reader_key]
        paras = current_book["paragraphs"]
        total_paras = len(paras)

        PARAS_PER_PAGE = 15
        total_pages = max(1, (total_paras + PARAS_PER_PAGE - 1) // PARAS_PER_PAGE)

        if st.session_state["reader_target_p"] > 1:
            calc_page = (st.session_state["reader_target_p"] - 1) // PARAS_PER_PAGE + 1
            st.session_state["reader_page"] = calc_page

        st.markdown(f"""
        <div style="background: #ffffff; border: 1px solid #e7e5e4; border-radius: 14px; padding: 18px 24px; margin-bottom: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
            <h2 style="margin: 0; color: #0c0a09; font-family: 'Frank Ruhl Libre', serif;">{current_book['title']}</h2>
            <span style="font-size: 13.5px; color: #78716c; font-weight: 600;">מיקום: {current_book['path']} · סה״כ {total_paras} פסקאות</span>
        </div>
        """, unsafe_allow_html=True)

        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        with nav_col1:
            if st.button("⬅️ עמוד קודם", use_container_width=True, disabled=(st.session_state["reader_page"] <= 1)):
                st.session_state["reader_page"] -= 1
                st.session_state["reader_target_p"] = 0
                st.rerun()

        with nav_col2:
            current_page = st.number_input(
                f"עמוד (מתוך {total_pages}):",
                min_value=1,
                max_value=total_pages,
                value=min(st.session_state["reader_page"], total_pages),
                step=1
            )
            st.session_state["reader_page"] = current_page

        with nav_col3:
            if st.button("עמוד הבא ➡️", use_container_width=True, disabled=(st.session_state["reader_page"] >= total_pages)):
                st.session_state["reader_page"] += 1
                st.session_state["reader_target_p"] = 0
                st.rerun()

        start_p_idx = (current_page - 1) * PARAS_PER_PAGE
        end_p_idx = min(start_p_idx + PARAS_PER_PAGE, total_paras)
        target_p = st.session_state.get("reader_target_p", 0)

        # תיבת הספר המרכזית
        st.markdown("<div style='max-width: 900px; margin: 0 auto; background: #ffffff; border: 1px solid #e7e5e4; border-radius: 16px; padding: 32px 40px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);'>", unsafe_allow_html=True)

        for p_i in range(start_p_idx, end_p_idx):
            para_num = p_i + 1
            p_text = paras[p_i]

            if para_num == target_p:
                st.markdown(f"""
                <div style="background-color: #fefce8; border-right: 5px solid #eab308; padding: 16px 20px; border-radius: 8px; margin-bottom: 24px;">
                    <span style="font-size: 13.5px; color: #854d0e; font-weight: 800;">📍 פסקה {para_num} (נמצאה בחיפוש):</span>
                    <div style="font-size: {font_size}px; line-height: 1.95; margin-top: 6px; color: #0c0a09; text-align: justify; font-weight: 600;">{p_text}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="margin-bottom: 22px; padding-bottom: 14px; border-bottom: 1px solid #f5f5f4;">
                    <span style="font-size: 12.5px; color: #a8a29e; font-weight: 800;">[{para_num}]</span>
                    <div style="font-size: {font_size}px; line-height: 1.95; margin-top: 4px; color: #292524; text-align: justify;">{p_text}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
        with b_col1:
            if st.button("⬅️ עמוד קודם ", key="bot_prev", use_container_width=True, disabled=(current_page <= 1)):
                st.session_state["reader_page"] -= 1
                st.session_state["reader_target_p"] = 0
                st.rerun()
        with b_col3:
            if st.button("עמוד הבא ➡️ ", key="bot_next", use_container_width=True, disabled=(current_page >= total_pages)):
                st.session_state["reader_page"] += 1
                st.session_state["reader_target_p"] = 0
                st.rerun()