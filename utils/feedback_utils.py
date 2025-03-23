from DB.index import database_manager
from agent import create_agent_executor

def fetch_and_summarize_feedback(email: str):
    database_manager.cursor.execute(
        """
        SELECT feedback_text FROM feedback WHERE email = %s ORDER BY created_at DESC LIMIT 10
        """,
        (email,),
    )
    feedback_entries = database_manager.cursor.fetchall()
    feedback_texts = [entry[0] for entry in feedback_entries]

    if not feedback_texts:
        return "No past feedback found."

    feedback_prompt = f"""
    Summarize the feedback of users to improve future prompts.

    Feedback entries: {feedback_texts}

    Provide in actionable format and make it short and concise. 
    Generalize the feedback to improve the model.
    """
    agent_executor = create_agent_executor()
    response = agent_executor.invoke({"input": feedback_prompt})
    return response.get("output", "").strip()
