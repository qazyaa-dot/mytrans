"""다국어 번역기 Streamlit 앱."""

import hmac

import streamlit as st

from translator import (
    MAX_CHARS,
    TARGET_LANGUAGES,
    TranslationError,
    load_config,
    translate,
)

st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")

st.markdown(
    """
    <style>
    .stApp p, .stApp h1, .stApp li { word-break: keep-all; }
    @media (max-width: 640px) { .stApp h1 { font-size: 2rem; } }
    .char-count { text-align: right; font-size: 0.85rem; color: #6b7280; margin-top: -0.5rem; }
    .char-count.over { color: #dc2626; font-weight: 600; }
    .subtitle { color: #6b7280; margin-top: -0.75rem; margin-bottom: 1.5rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def clear_result():
    st.session_state.pop("result", None)


def clear_input():
    st.session_state["input_text"] = ""
    clear_result()


def check_password(password: str) -> bool:
    """APP_PASSWORD가 설정되어 있으면 비밀번호를 입력해야 앱을 쓸 수 있다."""
    if st.session_state.get("authenticated"):
        return True
    st.title("🌐 다국어 번역기")
    with st.form("login"):
        entered = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("들어가기", type="primary", width="stretch")
    if submitted:
        if hmac.compare_digest(entered.encode(), password.encode()):
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("비밀번호가 올바르지 않습니다.")
    return False


config = load_config()
if config["password"] and not check_password(config["password"]):
    st.stop()

with st.sidebar:
    st.header("ℹ️ 정보")
    st.markdown(f"**사용 모델**  \n`{config['model']}`")
    st.markdown(
        "**사용 방법**\n"
        "1. 번역할 글을 입력합니다.\n"
        "2. **번역하기** 버튼을 누릅니다.\n"
        "3. 탭에서 언어별 결과를 확인하고 복사합니다."
    )
    st.caption("원문 언어는 자동으로 감지됩니다.")
    st.button("🗑️ 입력 지우기", on_click=clear_input, width="stretch")

st.title("🌐 다국어 번역기")
st.markdown(
    '<p class="subtitle">글을 입력하면 영어/일본어/스페인어로 번역합니다</p>',
    unsafe_allow_html=True,
)

if not config["api_key"]:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해 주세요.")

text = st.text_area(
    "번역할 글",
    key="input_text",
    on_change=clear_result,
    height=200,
    placeholder="번역할 글을 입력하세요...",
    label_visibility="collapsed",
)
over_class = " over" if len(text) > MAX_CHARS else ""
st.markdown(
    f'<div class="char-count{over_class}">{len(text):,} / {MAX_CHARS:,}자</div>',
    unsafe_allow_html=True,
)

if st.button(
    "번역하기", type="primary", width="stretch", disabled=not config["api_key"]
):
    if not text.strip():
        st.warning("번역할 글을 입력해 주세요.")
    elif len(text) > MAX_CHARS:
        st.warning(f"최대 {MAX_CHARS:,}자까지 입력할 수 있습니다.")
    else:
        with st.spinner("번역 중입니다..."):
            try:
                st.session_state["result"] = translate(text)
            except TranslationError as e:
                clear_result()
                st.error(str(e))

st.divider()

result = st.session_state.get("result")
tabs = st.tabs(list(TARGET_LANGUAGES.values()))
for tab, key in zip(tabs, TARGET_LANGUAGES):
    with tab:
        if result:
            st.code(result[key], language=None, wrap_lines=True)
            st.caption("오른쪽 위 아이콘을 눌러 복사할 수 있습니다.")
        else:
            st.info("번역 결과가 여기에 표시됩니다.")
