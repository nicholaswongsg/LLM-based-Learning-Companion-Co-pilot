import streamlit as st

from UI.StudentUI.Chat import ChatUI
from UI.StudentUI.Quiz import QuizUI
from UI.StudentUI.CoursePdf import UploadPdfUI
from UI.StudentUI.ContextPdf import pdf_context_upload_ui
from UI.common import init_student_ui_state

def StudentUI():
    init_student_ui_state()

    # Logout button at the top-right corner
    logout_col = st.columns([3, 1, 1])
    with logout_col[2]:
        if st.button("Logout", key="logout_btn"):
            # Clear session state
            st.session_state["logged_in"] = False
            st.session_state["email"] = None
            st.session_state["chat_history"] = []
            st.session_state["chat_history_ids"] = []
            st.session_state["last_user_input"] = None
            st.session_state.pop("quiz_data", None)
            st.session_state["show_pdf_upload_tab"] = False
            st.session_state["show_context_upload_tab"] = False
            st.rerun()

    # Use a single if–elif–elif–else chain:
    if st.session_state.get("show_pdf_upload_tab"):
        UploadPdfUI()
    elif st.session_state.get("show_context_upload_tab"):
        pdf_context_upload_ui()
    elif "quiz_data" in st.session_state:
        QuizUI()
    else:
        ChatUI()
