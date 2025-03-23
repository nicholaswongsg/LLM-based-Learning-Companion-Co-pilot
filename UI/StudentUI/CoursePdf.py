import streamlit as st

from API.pdf import pdf_handler
from UI.common import add_message_to_chat_history

def UploadPdfUI():
    st.subheader("Upload PDF Files to Create a New Course")

    # File uploader for multiple PDFs
    uploaded_files = st.file_uploader(
        "Upload one or more PDF files:",
        type=["pdf"],
        accept_multiple_files=True,
    )

    # Display the uploaded files
    if uploaded_files:
        st.write("Uploaded Files:")
        for file in uploaded_files:
            st.write(f"- {file.name}")

        # Input the user's email
        user_email = st.session_state.get("email")

        # Process the uploaded files
        if st.button("Generate Curriculum"):
            try:
                # Call the tool function to process PDFs
                result = pdf_handler.generate_curriculum(email=user_email, pdf_files=uploaded_files)

                # Save the result in session state for display in chat
                add_message_to_chat_history("assistant", result)

                st.success(result)

                # Exit the "Upload PDFs" interface
                st.session_state["show_pdf_upload_tab"] = False
                st.rerun()  # Refresh the interface to exit
            except Exception as e:
                st.error(f"Failed to process uploaded files: {e}")

    # Back to Main Chat button
    if st.button("Back to Learning Companion"):
        add_message_to_chat_history("assistant", "PDF upload to create new course was cancelled. How can I help you today?")
        st.session_state["show_pdf_upload_tab"] = False
        st.rerun()  # Rerun the app to return to the main chat UI
