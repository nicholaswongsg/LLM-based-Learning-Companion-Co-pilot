import json
import streamlit as st
import time

# Import chat and common UI functions.
from API.Chat.chat import chat_handler
from API.Chat.callback_handler import StreamlitCallbackHandler
from API.context import context_handler
from API.streak import streak_handler
from UI.common import add_feedback_for_message, add_message_to_chat_history
from UI.StudentUI.ContextPdf import pdf_context_upload_ui

# Import the transcribe and synthesize functions.
from utils.speech_service import transcribe_audio, synthesize_text
from utils.llm_utils import get_llm_fast

def generate_quick_replies(user_text):
    llm = get_llm_fast()
    prompt = f"Generate three short and natural-sounding responses to: '{user_text}'. Keep them under 10 words."
    
    response_obj = llm.invoke(prompt)
    response_text = response_obj.content  # Extract the actual text response
    
    print("response from llm", response_text)
    
    # Split the response by lines and strip out any empty ones
    lines = [line.strip() for line in response_text.split("\n") if line.strip()]
    
    # If fewer than 3 lines come back, just return a default set of 3
    if len(lines) < 3:
        return ["Yes", "No", "Tell me more"]
    
    # Otherwise, return the first 3 lines
    return lines[:3]


def MainChatUI():
    email = st.session_state.get("email")
    if email:
        streak_handler.update_user_streak(email)
        current_streak, longest_streak = streak_handler.get_streak(email)
        st.sidebar.write(f" **Keep Up Your Learning Streak**")
        st.sidebar.write(f"🔥 **Current Streak: {current_streak} days**")
        st.sidebar.write(f"🏆 **Longest Streak: {longest_streak} days**")

    # ---------- 1) Quiz UI Check ----------
    if st.session_state.get("current_ui") == "quiz_ui" and "quiz_data" in st.session_state:
        render_quiz_ui(st.session_state["quiz_data"])
        return

    # ---------- 2) Render Existing Conversation ----------
    for idx, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "conversation_id" in msg:
                if "feedback" in msg:
                    st.write("You have submitted feedback for this response!")
                else:
                    conversation_id = msg["conversation_id"]
                    with st.expander("Provide Feedback for Response"):
                        feedback_text = st.text_area("Feedback for Response", key=f"feedback_text_{idx}")
                        if st.button(f"Submit Feedback", key=f"feedback_submit_{idx}"):
                            try:
                                add_feedback_for_message(
                                    conversation_id=conversation_id, 
                                    feedback_text=feedback_text
                                )
                                st.success("Thank you for your feedback!")
                            except Exception as e:
                                st.error(f"Error: {e}")

    # ---------- 3) Process Quick Replies if Available ----------
    if "last_assistant_response" in st.session_state and st.session_state.last_assistant_response:
        quick_replies = generate_quick_replies(st.session_state.last_assistant_response)
        left, middle, right = st.columns(3)
        if left.button(quick_replies[0], use_container_width=True):
            st.session_state["user_text"] = quick_replies[0]
            st.rerun()
        if middle.button(quick_replies[1], use_container_width=True):
            st.session_state["user_text"] = quick_replies[1]
            st.rerun()
        if right.button(quick_replies[2], use_container_width=True):
            st.session_state["user_text"] = quick_replies[2]
            st.rerun()

    # ---------- 4) Prepare Audio Input Handling ----------
    # Initialize counter and processed_voice if not present.
    if "audio_input_counter" not in st.session_state:
        st.session_state.audio_input_counter = 0
    if "processed_voice" not in st.session_state:
        st.session_state.processed_voice = ""

    # Create a unique key for the audio input widget.
    audio_key = f"audio_input_widget_{st.session_state.audio_input_counter}"
    voice_audio = st.audio_input("Record a voice message", key=audio_key)
    voice_text = None
    if voice_audio is not None:
        # Transcribe the recorded audio.
        transcribed = transcribe_audio(voice_audio.getvalue())
        # Only process if non-empty and different from the one already processed.
        if transcribed and transcribed != st.session_state.processed_voice:
            voice_text = transcribed

    # ---------- 5) Process Voice Input (if available) ----------
    if voice_text:
        with st.chat_message("user"):
            st.markdown(voice_text)
        add_message_to_chat_history("user", voice_text)

        assistant_placeholder = st.chat_message("assistant")
        streamlit_handler = StreamlitCallbackHandler(assistant_placeholder)
        try:
            with st.spinner("Wait for it..."):
                response_data = chat_handler.conversational_rag_stream(
                    email=st.session_state["email"],
                    user_input=voice_text,
                    callback_handler=streamlit_handler,
                )
                
            # Ensure response_data is unpacked correctly
            if isinstance(response_data, tuple) and len(response_data) == 2:
                response, conversation_id = response_data
            else:
                raise ValueError("Unexpected return format from chat_handler.conversational_rag_stream()")

            assistant_response = streamlit_handler.get_final_text()
            print("DEBUG assistant_response:", assistant_response)
            print("DEBUG response:", response)

            st.session_state.last_assistant_response = assistant_response

            if response == "Uploading PDF to create course...":
                print("Inside PDF to create course")
                add_message_to_chat_history("assistant", response)
                st.session_state["show_pdf_upload_tab"] = True
                st.rerun()

            if response == "Uploading PDF for course context...":
                add_message_to_chat_history("assistant", response)
                st.session_state["show_context_upload_tab"] = True
                st.rerun()

            try:
                response_json = json.loads(assistant_response)
                if response_json.get("status") == "success" and "questions" in response_json:
                    st.session_state["quiz_data"] = response_json
                    st.session_state["current_ui"] = "quiz_ui"
                    # Replace the raw JSON response with a simple message.
                    assistant_response = "Quiz Initiated"
                # End quiz-check block.
            except json.JSONDecodeError:
                pass

            if conversation_id:
                add_message_to_chat_history("assistant", assistant_response, conversation_id=conversation_id)
            else:
                add_message_to_chat_history("assistant", assistant_response)
                st.warning("Failed to save conversation. Feedback will not be available.")

        except Exception as e:
            st.error(f"Error while processing voice input: {e}")

        # Mark this voice input as processed and increment the counter so the widget resets.
        st.session_state.processed_voice = voice_text
        st.session_state.audio_input_counter += 1

    # ---------- 6) Process Typed Input if Provided ----------
    if "user_text" in st.session_state and st.session_state["user_text"]:
        user_text = st.session_state.pop("user_text")
    else:
        user_text = st.chat_input("Type your message...")

    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        add_message_to_chat_history("user", user_text)

        assistant_placeholder = st.chat_message("assistant")
        streamlit_handler = StreamlitCallbackHandler(assistant_placeholder)
        try:
            with st.spinner("Wait for it..."):
                response_data = chat_handler.conversational_rag_stream(
                    email=st.session_state["email"],
                    user_input=user_text,
                    callback_handler=streamlit_handler,
                )

            if isinstance(response_data, tuple) and len(response_data) == 2:
                response, conversation_id = response_data
            else:
                raise ValueError("Unexpected return format from chat_handler.conversational_rag_stream()")

            assistant_response = streamlit_handler.get_final_text()
            print("DEBUG assistant_response:", assistant_response)
            print("DEBUG response:", response)

            st.session_state.last_assistant_response = assistant_response

            if response == "Uploading PDF to create course...":
                print("Inside PDF to create course")
                add_message_to_chat_history("assistant", response)
                st.session_state["show_pdf_upload_tab"] = True
                st.rerun()

            if response == "Uploading PDF for course context...":
                add_message_to_chat_history("assistant", response)
                st.session_state["show_context_upload_tab"] = True
                st.rerun()

            try:
                response_json = json.loads(assistant_response)
                if response_json.get("status") == "success" and "questions" in response_json:
                    st.session_state["quiz_data"] = response_json
                    st.session_state["current_ui"] = "quiz_ui"
                    # Replace the raw JSON response with a simple message.
                    assistant_response = "Quiz Initiated"
                # End quiz-check block.
            except json.JSONDecodeError:
                pass

            if conversation_id:
                add_message_to_chat_history("assistant", assistant_response, conversation_id=conversation_id)
            else:
                add_message_to_chat_history("assistant", assistant_response)
                st.warning("Failed to save conversation. Feedback will not be available.")
            st.rerun()
        except Exception as e:
            st.error(f"Error while processing text input: {e}")
    
    # ---------- 7) Button for Synthesis of Latest Assistant Response ----------
    if "last_assistant_response" in st.session_state and st.session_state.last_assistant_response:
        if st.button("Read Aloud"):
            with st.spinner("Synthesizing speech..."):
                audio_data = synthesize_text(st.session_state.last_assistant_response)
            if audio_data:
                st.audio(audio_data, format="audio/wav", start_time=0)
            else:
                st.error("Failed to synthesize speech.")

def render_quiz_ui(quiz_data):
    st.header("Quiz Time!")
    for idx, question in enumerate(quiz_data["questions"]):
        st.write(f"Q{idx + 1}: {question['question']}")
        for option in question.get("options", []):
            st.radio(f"Options for Q{idx + 1}", option, key=f"quiz_q{idx}_option")
    if st.button("Submit Quiz"):
        st.success("Thank you for submitting the quiz!")
        st.session_state["current_ui"] = "chat_ui"
        st.rerun()