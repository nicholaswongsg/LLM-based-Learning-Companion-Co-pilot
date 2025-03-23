import streamlit as st
from typing import List
from API.context import context_handler
from DB.index import database_manager
from UI.common import add_message_to_chat_history

def pdf_context_upload_ui():
    """
    UI to let users upload PDF(s) for adding context to their enrolled courses.
    """
    st.subheader("Upload PDF(s) to Add Context to Your Existing Courses")
    
    # Get the current user's email from session state
    user_email = st.session_state.get("email", "unknown@example.com")

    # Initialize pdf_processed flag in session_state if not present
    if "pdf_processed" not in st.session_state:
        st.session_state.pdf_processed = False

    # Query the database to retrieve courses for this user.
    try:
        query = "SELECT curriculum_id, subject FROM curriculums WHERE email = %s"
        database_manager.cursor.execute(query, (user_email,))
        # Expected output: [(curriculum_id, subject), ...]
        courses = database_manager.cursor.fetchall()
    except Exception as e:
        st.error("Error fetching courses: " + str(e))
        courses = []

    if courses:
        # Build mapping from course ID to a user-friendly label (e.g., subject)
        course_options = {str(course[0]): course[1] for course in courses}
        selected_course_id = st.selectbox(
            "Select the course to add PDF context to:",
            options=list(course_options.keys()),
            format_func=lambda cid: f"{course_options[cid]} (ID: {cid})"
        )
    else:
        st.info("No courses found. Please enroll in a course first.")
        selected_course_id = "default_course"

    # PDF uploader widget
    uploaded_pdfs = st.file_uploader(
        "Select one or more PDFs", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if uploaded_pdfs:
        if st.button("Process PDF(s) for Context"):
            with st.spinner("Processing..."):
                # Process PDFs (extract text, generate summary, create embeddings, and store the summary)
                extraction_result = context_handler.process_pdfs(
                    pdf_files=uploaded_pdfs,
                    user_email=user_email,
                    course_id=selected_course_id
                )

                if extraction_result:  # If processing was successful
                    st.session_state.pdf_processed = True  
                    # Display a summary of the extracted text length per file
                    for filename, text in extraction_result.items():
                        st.write(f"**{filename}** had {len(text)} characters extracted.")
                    st.success("PDF(s) processed successfully for context!")
    
    # Back to Main Chat button
    if st.button("Back to Learning Companion"):
        if not st.session_state.pdf_processed:
            add_message_to_chat_history("assistant", "PDF upload as context to your existing course was cancelled. How can I help you today?")
        else:
            add_message_to_chat_history("assistant", "PDF(s) have been successfully added to your course context! How can I assist your learning today?")
        st.session_state["show_context_upload_tab"] = False
        st.rerun()