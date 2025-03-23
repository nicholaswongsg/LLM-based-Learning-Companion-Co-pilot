from DB.index import database_manager
from utils.feedback_utils import fetch_and_summarize_feedback

class FeedbackHandler:
    def __init__(self):
        print("FeedbackHandler initialized.")

    def save_feedback(self, email: str, conversation_id: str, feedback_text: str):
        try:
            database_manager.cursor.execute(
                """
                INSERT INTO feedback (email, conversation_id, feedback_text)
                VALUES (%s, %s, %s)
                """,
                (email, conversation_id, feedback_text),
            )
            database_manager.cursor.connection.commit()
            print(f"[DEBUG] Feedback saved for {email}")

            # Fetch summarized feedback and RETURN it
            summarized_feedback = fetch_and_summarize_feedback(email)
            print(f"[DEBUG] New summarized feedback: {summarized_feedback}")
            return summarized_feedback

        except Exception as e:
            print(f"Error saving feedback: {e}")
            return None

    def fetch_feedback(self, email: str):
        database_manager.cursor.execute(
            """
            SELECT feedback_text FROM feedback WHERE email = %s ORDER BY created_at DESC LIMIT 10
            """,
            (email,),
        )
        feedback_entries = database_manager.cursor.fetchall()
        feedback_texts = [entry[0] for entry in feedback_entries]
        return feedback_texts if feedback_texts else []