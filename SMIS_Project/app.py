import streamlit as st
import google.generativeai as genai
import sqlite3
import hashlib
import time
from google.api_core.exceptions import ResourceExhausted

# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(
    page_title="SMIS miniAI v2.0",
    page_icon="🎓",
    layout="wide"
)

# -----------------------------------
# DATABASE SETUP
# -----------------------------------
conn = sqlite3.connect("chat_history.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats(
id INTEGER PRIMARY KEY AUTOINCREMENT,
role TEXT,
content TEXT
)
""")
conn.commit()

# -----------------------------------
# SESSION VARIABLES
# -----------------------------------
if "messages" not in st.session_state:
    cursor.execute("SELECT role,content FROM chats")
    st.session_state.messages = [
        {"role": r, "content": c} for r, c in cursor.fetchall()
    ]

if "request_count" not in st.session_state:
    st.session_state.request_count = 0

if "daily_limit" not in st.session_state:
    st.session_state.daily_limit = 18

if "cache" not in st.session_state:
    st.session_state.cache = {}

if "theme" not in st.session_state:
    st.session_state.theme = "Auto"

# -----------------------------------
# GEMINI CONFIG
# -----------------------------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# -----------------------------------
# AUTO THEME DETECTION
# -----------------------------------
theme_js = """
<script>
function getTheme(){
    const dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    return dark ? "dark" : "light"
}
window.parent.postMessage(
{theme:getTheme()}, "*"
)
</script>
"""
st.components.v1.html(theme_js,height=0)

def set_theme():

    if st.session_state.theme == "Dark":
        mode = "dark"
    elif st.session_state.theme == "Light":
        mode = "light"
    else:
        mode = "auto"

    if mode == "dark":
        st.markdown("""
        <style>
        .stApp{
        background:linear-gradient(135deg,#0E1117,#151923);
        color:#e6e6e6;
        }
        .stChatMessage{
        background:#1F2430;
        border-radius:16px;
        padding:10px;
        border:1px solid #2e3440;
        }
        </style>
        """,unsafe_allow_html=True)

    else:
        st.markdown("""
        <style>
        .stApp{
        background:linear-gradient(135deg,#f5f7fa,#e4ecf5);
        }
        .stChatMessage{
        background:white;
        border-radius:16px;
        padding:10px;
        border:1px solid #e5e7eb;
        }
        </style>
        """,unsafe_allow_html=True)

set_theme()

# -----------------------------------
# SIDEBAR
# -----------------------------------
with st.sidebar:

    st.title("🎓 SMIS miniAI")

    st.subheader("Theme")

    theme = st.radio(
        "Mode",
        ["Auto","Light","Dark"],
        index=["Auto","Light","Dark"].index(st.session_state.theme)
    )

    if theme != st.session_state.theme:
        st.session_state.theme = theme
        st.rerun()

    st.divider()

    if st.button("🧹 Clear Chat"):

        st.session_state.messages = []
        cursor.execute("DELETE FROM chats")
        conn.commit()

        st.rerun()

    st.divider()

    remaining = st.session_state.daily_limit - st.session_state.request_count

    st.subheader("AI Usage")

    st.progress(
        st.session_state.request_count /
        st.session_state.daily_limit
    )

    st.caption(f"Remaining Requests: {remaining}")

# -----------------------------------
# HERO HEADER
# -----------------------------------
st.markdown("""
<div style="
padding:25px;
border-radius:18px;
background:linear-gradient(90deg,#2563eb,#06b6d4);
color:white;
text-align:center;
box-shadow:0 8px 20px rgba(0,0,0,0.2);
">
<h1 style="color:white;">SMIS miniAI v2.0</h1>
<p>Startup-level AI academic assistant</p>
</div>
""",unsafe_allow_html=True)

# -----------------------------------
# CACHE KEY
# -----------------------------------
def cache_key(prompt):
    return hashlib.md5(prompt.encode()).hexdigest()

# -----------------------------------
# SAFE AI REQUEST
# -----------------------------------
def ask_ai(prompt):

    if st.session_state.request_count >= st.session_state.daily_limit:
        return "⚠️ Daily request limit reached."

    key = cache_key(prompt)

    if key in st.session_state.cache:
        return st.session_state.cache[key]

    for _ in range(3):

        try:

            response = model.generate_content(prompt)

            answer = response.text

            st.session_state.cache[key] = answer
            st.session_state.request_count += 1

            return answer

        except ResourceExhausted:

            time.sleep(6)

    return "⚠️ AI quota exceeded."

# -----------------------------------
# DISPLAY CHAT
# -----------------------------------
for msg in st.session_state.messages:

    avatar = "🎓" if msg["role"]=="assistant" else "👤"

    with st.chat_message(msg["role"],avatar=avatar):
        st.markdown(msg["content"])

# -----------------------------------
# USER INPUT
# -----------------------------------
prompt = st.chat_input("Ask SMIS miniAI...")

if prompt:

    st.session_state.messages.append(
        {"role":"user","content":prompt}
    )

    cursor.execute(
        "INSERT INTO chats(role,content) VALUES(?,?)",
        ("user",prompt)
    )
    conn.commit()

    with st.chat_message("user",avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant",avatar="🎓"):

        with st.spinner("Thinking..."):

            reply = ask_ai(
                f"You are SMIS miniAI, a helpful university assistant. User: {prompt}"
            )

            placeholder = st.empty()

            text=""

            for char in reply:
                text+=char
                placeholder.markdown(text)
                time.sleep(0.01)

    st.session_state.messages.append(
        {"role":"assistant","content":reply}
    )

    cursor.execute(
        "INSERT INTO chats(role,content) VALUES(?,?)",
        ("assistant",reply)
    )
    conn.commit()