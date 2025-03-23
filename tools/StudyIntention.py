from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from DB.index import database_manager
from API.curriculum import curriculum_handler
from UI.common import add_message_to_chat_history

from concurrent.futures import ThreadPoolExecutor

# Thread pool for background tasks
background_executor = ThreadPoolExecutor(max_workers=4)


class Chapter(BaseModel):
    title: str = Field(description="Title of the chapter")
    description: str = Field(description="Description about the chapter")


class CurriculumDetails(BaseModel):
    description: str = Field(description="Detailed curriculum generated")
    chapters: list[Chapter] = Field(
        description="List of chapters the user needs to go through"
    )


class FormInput(BaseModel):
    topic: str = Field(description="Topic that user wants to learn")
    commitment_level: str = Field(
        description="Commitment frequency (Daily, Weekly, Twice a Week, Monthly)"
    )
    duration_session: str = Field(
        description="How many minutes the user wants to learn each session"
    )
    start_date: str = Field(description="Date the user wants to start (YYYY-MM-DD)")
    learning_goal: str = Field(description="Why the user wants to learn this subject")
    curriculum_details: CurriculumDetails = Field(
        description="Detailed curriculum based on user inputs"
    )


def write_into_db(
    email: str,
    topic: str,
    commitment_level: str,
    duration_session: str,
    start_date: str,
    learning_goal: str,
    curriculum_details: CurriculumDetails,
):
    print("[DEBUG] Writing into DB:", email, topic, commitment_level, duration_session, start_date, learning_goal)
    
    # Check if a similar curriculum already exists
    try:
        database_manager.cursor.execute(
            """
            SELECT curriculum_id FROM curriculums
            WHERE email = %s
              AND subject = %s
              AND start_date = %s
              AND goal_description = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email, topic, start_date, curriculum_details.description),
        )
        existing = database_manager.cursor.fetchone()
        print(f"[DEBUG] Existing curriculum: {existing}")
    except Exception as e:
        print(f"[ERROR] Failed to execute SELECT query: {e}")
        return

    if existing:
        print("[DEBUG] Curriculum already exists. Skipping creation.")
        return existing[0]

    # Save new curriculum if it doesn't exist
    try:
        curriculum_id = curriculum_handler.save_curriculum_with_chapters(
            email=email,
            subject=topic,
            goal_description=curriculum_details.description,
            commitment_level=commitment_level,
            duration_per_session=duration_session,
            start_date=start_date,
            learning_goal=learning_goal,
        )
        if curriculum_id:
            print(f"[DEBUG] Curriculum stored successfully with ID: {curriculum_id}")
        else:
            print("[ERROR] Failed to store curriculum.")
        return curriculum_id
    except Exception as e:
        print(f"[ERROR] Failed to save curriculum: {e}")

def get_user_study_intention(
    email: str,
    topic: str,
    commitment_level: str,
    duration_session: str,
    start_date: str,
    learning_goal: str,
    curriculum_details: CurriculumDetails,
) -> str:
    """
    Instead of generating and storing the curriculum synchronously,
    we offload that work to a background thread.
    """

    # write_into_db(
    # Submit the DB-writing (including the LLM-based generation) to a background thread
    background_executor.submit(
        write_into_db,
        email=email,
        topic=topic,
        commitment_level=commitment_level,
        duration_session=duration_session,
        start_date=start_date,
        learning_goal=learning_goal,
        curriculum_details=curriculum_details,
    )
    
    course_generation="Your course is being generated in the background. You will be notified once it is ready."
    
    # Append feedback to chat history
    add_message_to_chat_history("assistant", course_generation)
    
    return "Your personalized curriculum has been generated and stored."


def get_study_intention_tool(email: str):
    return StructuredTool.from_function(
        func=lambda topic, commitment_level, duration_session, start_date, learning_goal, curriculum_details: get_user_study_intention(
            email,
            topic,
            commitment_level,
            duration_session,
            start_date,
            learning_goal,
            curriculum_details,
        ),
        name="StudyIntention",
        description="Notify about user's learning intention and produce/store a curriculum",
        args_schema=FormInput,
        return_direct=False,
    )
