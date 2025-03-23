import streamlit as st
import re

from DB.index import database_manager
from agent import create_agent_executor
from API.curriculum import curriculum_handler
from API.Chat.chat import chat_handler
from UI.common import add_message_to_chat_history
from utils.memory_utils import get_user_memory

def fetch_curriculum_id(chapter_id):
    """
    Fetch the curriculum_id for a given chapter_id.
    """
    try:
        database_manager.cursor.execute(
            """
            SELECT curriculum_id 
            FROM curriculum_chapters 
            WHERE chapter_id = %s
            """,
            (chapter_id,),
        )
        curriculum_data = database_manager.cursor.fetchone()
        return curriculum_data[0] if curriculum_data else None
    except Exception as e:
        st.error(f"Error fetching curriculum ID: {e}")
        return None

def determine_completion_status(chapter_id, user_email, score, total_questions, reflection_after_quiz):
    """
    Use LLM to determine if the chapter should be marked as complete based on performance and reflection.
    """
    prompt = f"""
    The user just completed a chapter quiz.

    Chapter ID: {chapter_id}
    User Email: {user_email}
    Score: {score}/{total_questions}
    Reflection: "{reflection_after_quiz}"

    Determine if the user shows strong understanding and is ready to mark the chapter as completed.
    If the user performed well and their reflection indicates they have understood the material deeply, respond with 'complete'.
    Otherwise, respond with 'incomplete'.
    """
    try:
        agent_executor = create_agent_executor()
        response = agent_executor.invoke({"input": prompt})
        return response.get("output", "").strip()
    except Exception as e:
        st.error(f"Error determining completion status: {e}")
        return "incomplete"

def update_chapter_status(chapter_id, status):
    try:
        is_completed = status.lower() == "passed"
        print(f"[DEBUG] Updating chapter_id {chapter_id} to {'Completed' if is_completed else 'Not Completed'}")

        database_manager.cursor.execute(
            """
            UPDATE curriculum_chapters
            SET is_completed = %s
            WHERE chapter_id = %s
            """,
            (is_completed, chapter_id),
        )
        database_manager.cursor.connection.commit()
        print(f"[DEBUG] Chapter {chapter_id} update committed successfully.")
        return True
    except Exception as e:
        st.error(f"Failed to update chapter status: {e}")
        print(f"[ERROR] Failed to update chapter status for chapter_id {chapter_id}: {e}")
        return False

def mark_chapter_completed_if_ready(chapter_id, user_email, score, total_questions, reflection_after_quiz):
    """
    Determine if the user is ready to mark the chapter as completed based on their quiz performance and reflection.
    Provide a review of the results and recommend the next chapter.
    """
    curriculum_id = fetch_curriculum_id(chapter_id)
    if not curriculum_id:
        st.error("Failed to fetch curriculum details for the chapter.")
        return

    # Determine completion status using LLM
    reasoning_prompt = f"""
    The user just completed a chapter quiz.

    Chapter ID: {chapter_id}
    Score: {score}/{total_questions}
    Reflection: "{reflection_after_quiz}"

    1. Provide detailed feedback on the user's performance. Highlight areas where they excelled and areas where they need improvement.
    2. Recommend the next chapter of the course the user should take based on their current progress.
    3. Respond with 'Passed' if the user is ready to complete this chapter, or 'Failed' if they need more practice.
    4. You must end off with a question to the user like "Would you like to continue learning?".
    """
    try:
        agent_executor = create_agent_executor()
        response = agent_executor.invoke({"input": reasoning_prompt})
        llm_feedback = response.get("output", "").strip()

        # Append feedback to chat history
        add_message_to_chat_history("assistant", llm_feedback)

        # # Appending to LLM Memory
        # chat_handler.memory.save_context(
        #     {"input": "Quiz feedback message (assistant)"},
        #     {"output": llm_feedback},
        # )

        # Append feedback to ChatHandler memory for this specific user
        user_memory = get_user_memory(chat_handler.user_memories, user_email)
        user_memory.save_context(
            {"input": "Quiz feedback message (assistant)"},
            {"output": llm_feedback},
        )
    except Exception as e:
        st.error(f"Error generating feedback and next steps: {e}")
        return
    
    sanitized_feedback = re.sub(r"[^\w\s]", "", llm_feedback).lower()
    
    # Parse LLM feedback to determine completion status
    if "passed" in sanitized_feedback:
        completion_status = "Passed"
    elif score == total_questions:  # Fallback: Perfect score
        completion_status = "Passed"
    else:
        completion_status = "Failed"

    # Update the chapter status in the database
    if completion_status == "Passed":
        status_updated = update_chapter_status(chapter_id, "Passed")
        if status_updated:
            st.info("The chapter has been marked as completed based on your performance and reflection.")
        else:
            st.error(f"Failed to mark chapter {chapter_id} as completed. Check logs for details.")
    else:
        st.info("It seems you may need more practice before marking this chapter as complete.")

    # Fetch and analyze curriculum for improvements
    # try:
    #     curriculum_handler.fetch_analyze_and_improve_curriculum(curriculum_id)
    # except Exception as e:
    #     st.error(f"Error analyzing curriculum: {e}")

def QuizUI():
    quiz_data = st.session_state.get("quiz_data", {})
    print("[DEBUG] render_quiz_form...")

    # Check if quiz data is valid
    if not quiz_data or quiz_data.get("status") != "success" or "questions" not in quiz_data:
        st.write("No quiz questions available.")
        return

    # Reset state when quiz data changes
    if "current_quiz_id" not in st.session_state or st.session_state.get("current_quiz_id") != quiz_data.get("chapter_id"):
        st.session_state.current_quiz_id = quiz_data.get("chapter_id")
        st.session_state.quiz_submitted = False
        st.session_state.user_answers = {}  # Reset answers for the new quiz

    # Ensure chapter_id and email are available
    chapter_id = quiz_data.get("chapter_id")
    user_email = quiz_data.get("email")
    if chapter_id is None or user_email is None:
        st.error("Missing chapter_id or user email for quiz submission.")
        return

    # Display the quiz
    st.write("### Quiz Time!")
    st.write("Answer the following questions:")

    for i, question in enumerate(quiz_data["questions"], start=1):
        st.write(f"**Q{i}: {question['question']}**")

        # Restore the selected option or default to None
        previous_answer = st.session_state.user_answers.get(f"q{i}")
        if previous_answer in question["options"]:
            selected_index = question["options"].index(previous_answer)
        else:
            selected_index = None  # Default to no selection

        # Render the radio button
        selected_option = st.radio(
            label=f"Select your answer for Q{i}",
            options=question["options"],
            key=f"quiz_q{i}_{chapter_id}",  # Unique key for each question
            index=selected_index if selected_index is not None else 0,
        )
        st.session_state.user_answers[f"q{i}"] = selected_option

    # Reflection input
    reflection_after_quiz = st.text_area(
        "What did you learn from this quiz? Reflect on what you just learned or found challenging.",
        key=f"reflection_input_{chapter_id}",
    )

    # Submit button logic
    if not st.session_state.quiz_submitted:
        if st.button("Submit Answers", key=f"submit_button_{chapter_id}"):
            # Ensure reflection is provided
            if not reflection_after_quiz.strip():
                st.error("Reflection is required to complete the quiz. Please provide your thoughts.")
                return

            # Calculate score
            correct_count = 0
            for i, question in enumerate(quiz_data["questions"], start=1):
                correct_option = question["options"][ord(question["correct_option"]) - ord("A")]
                if st.session_state.user_answers.get(f"q{i}") == correct_option:
                    correct_count += 1

            # Save quiz results
            try:
                database_manager.cursor.execute(
                    """
                    INSERT INTO quiz_results (chapter_id, email, score, reflection_after_quiz)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (chapter_id, user_email, correct_count, reflection_after_quiz),
                )
                database_manager.cursor.connection.commit()
            except Exception as e:
                st.error(f"Failed to save quiz results: {e}")

            st.success(f"You scored {correct_count}/{len(quiz_data['questions'])}!")

            # Analyze performance and mark completion
            mark_chapter_completed_if_ready(
                chapter_id,
                user_email,
                correct_count,
                len(quiz_data["questions"]),
                reflection_after_quiz,
            )

            st.session_state.quiz_submitted = True  # Update submission state

    # Back button logic
    if st.session_state.quiz_submitted:
        if st.button("Back to Learning Companion", key=f"back_button_{chapter_id}"):
            # Clear quiz data to ensure returning to main UI
            st.session_state.pop("quiz_data", None)
            st.session_state.pop("current_quiz_id", None)
            st.session_state.quiz_submitted = False
            # Redirect to main chat interface
            st.experimental_set_query_params(view="chat")
            st.rerun()
