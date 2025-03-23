import json
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from DB.index import database_manager
from API.curriculum import curriculum_handler


class StartQuizInput(BaseModel):
    chapter_id: int = Field(
        description="The ID of the chapter for which the user wants to start the quiz"
    )


def start_quiz(chapter_id: int, email: str):
    print("[DEBUG] Starting quiz for chapter ID", chapter_id)
    """
    Fetch questions for a given chapter ID and return them as a structured JSON.
    """
    # Validate chapter
    database_manager.cursor.execute(
        "SELECT chapter_id FROM curriculum_chapters WHERE chapter_id = %s",
        (chapter_id,),
    )
    if not database_manager.cursor.fetchone():
        return json.dumps(
            {"status": "error", "message": "Invalid chapter ID provided."}
        )

    # Fetch quiz questions
    questions = curriculum_handler.fetch_quiz_questions_data(chapter_id)
    if not questions:
        return json.dumps(
            {
                "status": "error",
                "message": f"No quiz questions found for Chapter ID {chapter_id}.",
            }
        )

    # Return questions as structured JSON
    formatted_questions = [
        {"question": q[0], "options": [q[1], q[2], q[3], q[4]], "correct_option": q[5]}
        for q in questions
    ]

    return f'Respond with this JSON object only {json.dumps({"status": "success", "email": email, "chapter_id": chapter_id, "questions": formatted_questions})}'


def get_start_quiz_tool(email: str):
    return StructuredTool.from_function(
        func=lambda chapter_id: start_quiz(chapter_id, email),
        name="StartQuiz",
        description="Use this tool to start or continue to the MCQ quiz for a given chapter. Response user with JSON object only.",
        args_schema=StartQuizInput,
        return_direct=False,
    )
