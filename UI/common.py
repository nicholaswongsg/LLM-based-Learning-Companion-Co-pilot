import streamlit as st

from typing import Optional

from API.feedback import FeedbackHandler

feedback_handler = FeedbackHandler()

def add_feedback_for_message(conversation_id: str, feedback_text: str):
    email = st.session_state["email"]
    summarized_feedback = feedback_handler.save_feedback(
        email, conversation_id, feedback_text
    )
    # Flag session state indicating feedback was updated
    st.session_state["feedback_updated"] = True

    # Update chat history visually
    for msg in st.session_state.chat_history:
        if "conversation_id" in msg and msg["conversation_id"] == conversation_id:
            msg["feedback"] = feedback_text
            
def add_message_to_chat_history(
    role: str, content: str, conversation_id: Optional[str] = None
):
    message = {"role": role, "content": content}
    if conversation_id:
        message.update({"conversation_id": conversation_id})
    st.session_state.chat_history.append(message)


def init_student_ui_state():
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
        add_message_to_chat_history(
            "assistant",
            """
            Welcome to Your AI Learning Companion! 🎓

            I'm here to help you stay on track with your studies, whether it's enrolling in new courses, continuing where you left off, or retrieving course materials. Here’s what you can do:

            ✅ Continue Learning – Pick up where you left off or explore new topics.

            📚 Retrieve Course Materials – Access your uploaded PDF to your enrolled courses.

            📝 Take Quizzes – Test your knowledge with interactive quizzes.

            🚀 Start a New Course – Let me guide you through a structured learning path.

            🔍 Get Study Help – If you need clarification, I can fetch relevant materials or escalate to your school instructor.

            Let’s get started! Would you like to continue your scheduled topic for today, or explore something new? 😊
            
            """,
        
        )

    if "last_user_input" not in st.session_state:
        st.session_state["last_user_input"] = None

    if "show_pdf_upload_tab" not in st.session_state:
        st.session_state["show_pdf_upload_tab"] = False

    if "show_context_upload_tab" not in st.session_state:
        st.session_state["show_context_upload_tab"] = False