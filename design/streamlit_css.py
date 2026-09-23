"""
design/streamlit_css.py — Arco Design System CSS adapted for Streamlit.

Streamlit renders inside an iframe and uses specific CSS class names that
change between versions. This module provides the CSS string injected via
st.markdown(..., unsafe_allow_html=True) in app.py.

To update styles: edit ARCO_CSS here and keep design/arco.css in sync.
"""

ARCO_CSS = """
<style>
/* ════════════════════════════════════════════════════════════════════════════
   ARCO DESIGN SYSTEM — Streamlit adaptation
   Source tokens: design/tokens.py  |  Reference CSS: design/arco.css
   ════════════════════════════════════════════════════════════════════════════ */

/* ── Global reset & typography ── */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
                 "Helvetica Neue", Helvetica, Arial, sans-serif !important;
    color: #1D2129;
    -webkit-font-smoothing: antialiased;
}

/* ── Page background ── */
.stApp {
    background-color: #F2F3F5;
}

/* ── Main content area — white card ── */
section.main > div {
    background-color: #FFFFFF;
    border-radius: 8px;
    padding: 24px 32px 32px 32px;
    margin: 16px 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.08), 0 0 2px rgba(0,0,0,0.05);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E6EB;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 24px;
}

/* ── Headings ── */
h1 {
    font-size: 20px !important;
    font-weight: 600 !important;
    color: #1D2129 !important;
    line-height: 1.4 !important;
    margin-bottom: 4px !important;
}

h2 {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #1D2129 !important;
    margin-bottom: 12px !important;
}

h3 {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #1D2129 !important;
}

/* Streamlit subheader */
[data-testid="stHeading"] h2,
.stHeading h2 {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #1D2129 !important;
    border-bottom: 1px solid #E5E6EB;
    padding-bottom: 10px;
    margin-bottom: 16px !important;
}

/* ── Caption / small text ── */
.stCaption, [data-testid="stCaptionContainer"] p {
    font-size: 12px !important;
    color: #86909C !important;
}

/* ── Primary button ── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background-color: #165DFF !important;
    border: 1px solid #165DFF !important;
    border-radius: 4px !important;
    color: #FFFFFF !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    height: 36px !important;
    padding: 0 20px !important;
    transition: all 0.1s cubic-bezier(0, 0, 1, 1) !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    background-color: #4080FF !important;
    border-color: #4080FF !important;
}

.stButton > button[kind="primary"]:active,
.stButton > button[data-testid="baseButton-primary"]:active {
    background-color: #0E42D2 !important;
    border-color: #0E42D2 !important;
}

.stButton > button[kind="primary"]:disabled,
.stButton > button[data-testid="baseButton-primary"]:disabled {
    background-color: #C9CDD4 !important;
    border-color: #C9CDD4 !important;
    cursor: not-allowed !important;
}

/* ── Secondary button ── */
.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E5E6EB !important;
    border-radius: 4px !important;
    color: #1D2129 !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    height: 36px !important;
    transition: all 0.1s cubic-bezier(0, 0, 1, 1) !important;
    box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover {
    border-color: #165DFF !important;
    color: #165DFF !important;
}

/* ── Text inputs ── */
.stTextInput > label,
.stTextArea > label,
.stSelectbox > label,
.stFileUploader > label {
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #1D2129 !important;
    margin-bottom: 4px !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border: 1px solid #E5E6EB !important;
    border-radius: 4px !important;
    font-size: 14px !important;
    color: #1D2129 !important;
    background-color: #FFFFFF !important;
    padding: 6px 12px !important;
    transition: border-color 0.1s !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #165DFF !important;
    box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.15) !important;
    outline: none !important;
}

.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #86909C !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    border: 1px solid #E5E6EB !important;
    border-radius: 4px !important;
    font-size: 14px !important;
    background-color: #FFFFFF !important;
}

.stSelectbox > div > div:focus-within {
    border-color: #165DFF !important;
    box-shadow: 0 0 0 2px rgba(22, 93, 255, 0.15) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 1px dashed #C9CDD4 !important;
    border-radius: 8px !important;
    background-color: #F7F8FA !important;
    padding: 20px !important;
    transition: border-color 0.2s !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: #165DFF !important;
    background-color: #E8F3FF !important;
}

[data-testid="stFileUploader"] p {
    font-size: 13px !important;
    color: #4E5969 !important;
}

/* ── Alerts / Info boxes ── */
[data-testid="stAlert"] {
    border-radius: 6px !important;
    font-size: 14px !important;
    border: none !important;
    padding: 12px 16px !important;
}

/* Info (blue) */
[data-testid="stAlert"][kind="info"],
div[data-baseweb="notification"][kind="info"] {
    background-color: #E8F3FF !important;
    border-left: 3px solid #165DFF !important;
    color: #1D2129 !important;
}

/* Success (green) */
[data-testid="stAlert"][kind="success"],
div[data-baseweb="notification"][kind="positive"] {
    background-color: #E8FFEA !important;
    border-left: 3px solid #00B42A !important;
}

/* Warning (orange) */
[data-testid="stAlert"][kind="warning"],
div[data-baseweb="notification"][kind="warning"] {
    background-color: #FFF7E8 !important;
    border-left: 3px solid #FF7D00 !important;
}

/* Error (red) */
[data-testid="stAlert"][kind="error"],
div[data-baseweb="notification"][kind="negative"] {
    background-color: #FFECE8 !important;
    border-left: 3px solid #F53F3F !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid #E5E6EB !important;
    margin: 20px 0 !important;
}

/* ── Data table / dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E5E6EB !important;
    border-radius: 6px !important;
    overflow: hidden !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #E5E6EB !important;
    border-radius: 6px !important;
    background-color: #FFFFFF !important;
    margin-bottom: 8px !important;
}

[data-testid="stExpander"] summary {
    font-weight: 500 !important;
    font-size: 14px !important;
    color: #1D2129 !important;
    padding: 10px 14px !important;
}

[data-testid="stExpander"] summary:hover {
    background-color: #F7F8FA !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] p {
    font-size: 14px !important;
    color: #4E5969 !important;
}

/* ── Sidebar header labels ── */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-size: 13px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    color: #86909C !important;
    border-bottom: none !important;
    padding-bottom: 0 !important;
}

/* ── Success badge ── */
.arco-badge-success {
    background-color: #E8FFEA;
    color: #00B42A;
    border-radius: 2px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 500;
}
</style>
"""
