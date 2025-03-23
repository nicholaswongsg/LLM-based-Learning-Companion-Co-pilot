import re
import json
import time
from typing import Callable, Optional
from datetime import datetime, timedelta
from fuzzywuzzy import process
from concurrent.futures import ThreadPoolExecutor

from langchain.schema import HumanMessage

from utils.llm_utils import get_llm, get_llm_fast
from DB.index import database_manager
from agent import create_agent_executor

# Thread pool for background tasks
background_executor = ThreadPoolExecutor(max_workers=10)

class CurriculumHandler:
    def __init__(self):
        print("CurriculumHandler initialized!")

    def generate_chapter_lesson(self, subject: str, chapter_title: str, chapter_description: str) -> str:
        """
        Creates a step-by-step lesson plan from the LLM for the chapter.
        Returns the lesson plan text.
        """

        llm = get_llm()
        prompt = f"""
        You are a highly experienced and engaging teacher with expertise in making complex topics accessible.
        The user is studying the course: {subject}
        Chapter Title: "{chapter_title}"
        Chapter Description: "{chapter_description}"

        Create a comprehensive, step-by-step lesson plan for this chapter. Include:
        1) Key Learning Objectives
        2) Core Content (explanations, real-world examples, questions)
        3) Interactive Exercises
        4) Conclusion and Recap

        Ask the user if they have any questions at the end.
        """

        response = llm([HumanMessage(content=prompt)])
        return response.content.strip()
    
    def get_next_chapter_to_learn(
    self, email: str, subject: str, on_continue_course: Optional[Callable[[str, int, str], None]] = None
) -> str:
        # Fetch next chapter data
        chapter_data, error_message = self.get_next_chapter_data(email, subject)
        if error_message:
            return error_message

        chapter_id, chapter_title, chapter_description, matched_subject = chapter_data

        # Check if quiz already exists
        database_manager.cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM quiz_questions WHERE chapter_id = %s)", 
            (chapter_id,)
        )
        quiz_exists = database_manager.cursor.fetchone()[0]

        # Generate lesson content and quiz concurrently
        lesson_future = background_executor.submit(
            self.generate_chapter_lesson, matched_subject, chapter_title, chapter_description
        )
        if not quiz_exists:
            background_executor.submit(generate_quiz_for_chapter, chapter_id, chapter_title, chapter_description)

        # Wait for the lesson content to complete
        lesson_content = lesson_future.result()
        quiz_status = "Quiz ready" if quiz_exists else "Quiz will be available after the lesson."

        # Optionally call the callback after lesson content is ready
        if on_continue_course:
            on_continue_course(
                subject=matched_subject,
                chapter_id=chapter_id,
                generated_content=lesson_content,
            )

        return json.dumps({
            "chapter_id": chapter_id,
            "user_message": (f"{lesson_content}\n\n{quiz_status}",
                             "Are you ready to take the MCQ quiz to test your understanding?"
            )
            
        })

    def get_next_chapter_data(self, email: str, subject: str):
        normalized_subject = get_closest_subject(email, subject)
        if not normalized_subject:
            return None, f"No enrolled course found for subject: {subject}. Please check the course name."

        # SINGLE QUERY: retrieve the newest curriculum + next incomplete chapter
        database_manager.cursor.execute(
            """
            SELECT c.chapter_id, c.title, c.description, cu.subject
            FROM curriculums cu
            JOIN curriculum_chapters c 
                ON cu.curriculum_id = c.curriculum_id
            WHERE cu.email = %s
            AND LOWER(cu.subject) = LOWER(%s)
            AND (c.is_completed = FALSE OR c.is_completed IS NULL)
            ORDER BY cu.created_at DESC, c.chapter_id ASC
            LIMIT 1
            """,
            (email, normalized_subject),
        )
        row = database_manager.cursor.fetchone()
        
        if not row:
            # Could be no incomplete chapters OR no curriculum at all
            return None, f"You have completed all chapters for the {normalized_subject} course. Congratulations!"

        chapter_id, chapter_title, chapter_description, matched_subject = row
        return (chapter_id, chapter_title, chapter_description, matched_subject), None

    def calculate_scheduled_dates(self, commitment_level: str, start_date: str, total_chapters: int) -> list:
        """Calculate the scheduled dates for chapters based on commitment level."""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        days_interval = {
            "Daily": 1,
            "Weekly": 7,
            "Twice a Week": 3.5,
            "Monthly": 30,
        }.get(commitment_level, 7)

        scheduled_dates = [
            start + timedelta(days=int(days_interval * i))
            for i in range(total_chapters)
        ]
        return scheduled_dates

    def save_curriculum_with_chapters(
        self,
        email,
        subject,
        goal_description,
        commitment_level,
        duration_per_session,
        start_date,
        learning_goal,
    ):
        """
        Uses LLM to generate chapters for a given subject, then
        saves curriculum & chapters to the database.
        """
        print(f"[DEBUG] Generating chapters for subject: {subject}")

        llm = get_llm_fast()

        chapter_request = f"""
        Generate a JSON course outline for '{subject}' with chapters. 
        Each chapter should have 'title' and 'description' keys.
        """

        response = llm([{"role": "user", "content": chapter_request}])

        content = response.content.strip()
        print(f"[DEBUG] LLM response: {content}")

        # Extract JSON of chapters
        try:
            chapters = json.loads(content)
        except json.JSONDecodeError:
            json_text = re.search(r"(\[.*\])", content, re.DOTALL)
            if json_text:
                chapters = json.loads(json_text.group(1))
            else:
                print("Failed to parse JSON from the assistant's response for chapters.")
                return None
            
        # Validate
        if not isinstance(chapters, list) or not all(isinstance(ch, dict) for ch in chapters):
            print("Chapters JSON is not in the expected list-of-dicts format.")
            return None

        # Calculate scheduled dates
        total_chapters = len(chapters)
        scheduled_dates = self.calculate_scheduled_dates(commitment_level, start_date, total_chapters)

        # Insert the curriculum
        try:
            database_manager.cursor.execute(
                """
                INSERT INTO curriculums (email, subject, goal_description, commitment_level, duration_per_session, 
                                         start_date, learning_goal, created_at)
                VALUES (
                    %s, 
                    INITCAP(SUBSTRING(%s FROM 1 FOR 1)) || LOWER(SUBSTRING(%s FROM 2)),
                    %s, %s, %s, %s, %s, %s
                ) RETURNING curriculum_id
                """,
                (
                    email,
                    subject,
                    subject,
                    goal_description,
                    commitment_level,
                    duration_per_session.split()[0],
                    start_date,
                    learning_goal,
                    datetime.now(),
                ),
            )
            curriculum_id = database_manager.cursor.fetchone()[0]

            # Prepare data for batch insertion
            chapters_data = [
                (curriculum_id, chapter.get("title", "").strip()[:255], chapter.get("description", "").strip(), scheduled_dates[i])
                for i, chapter in enumerate(chapters)
            ]

            # Perform batch insert
            future = background_executor.submit(
                database_manager.cursor.executemany,
                """
                INSERT INTO curriculum_chapters (curriculum_id, title, description, scheduled_date)
                VALUES (%s, %s, %s, %s)
                """,
                chapters_data,
            )
            future.result()  # blocks until done
            database_manager.cursor.connection.commit()
            return curriculum_id

        except Exception as e:
            print(f"Error inserting curriculum or chapters: {e}")
            return None

    def get_current_enrollment(self, email: str) -> str:
        database_manager.cursor.execute(
            """
            SELECT curriculum_id, subject, start_date, commitment_level, duration_per_session, 
                   goal_description, learning_goal, created_at
            FROM curriculums
            WHERE email = %s
            ORDER BY created_at DESC
            """,
            (email,),
        )

        rows = database_manager.cursor.fetchall()
        if not rows:
            return "You are not currently enrolled in any course."

        result = "You are currently enrolled in the following courses:\n"
        for (
            curriculum_id,
            subject,
            start_date,
            commitment_level,
            duration_per_session,
            goal_description,
            learning_goal,
            created_at,
        ) in rows:
            result += f"""
            **Course ID:** {curriculum_id}
            **Course:** {subject}
            **Start Date:** {start_date}
            **Commitment Level:** {commitment_level}
            **Duration per Session:** {duration_per_session} minutes
            **Goal Description:** {goal_description if goal_description else 'N/A'}
            **Learning Goal:** {learning_goal if learning_goal else 'N/A'}
            Enrolled on: {created_at.strftime('%Y-%m-%d %H:%M:%S')}
    """
        return result.strip()

    def fetch_quiz_questions_data(self, chapter_id: int):
        """
        Fetch quiz questions data for displaying in a form or UI.
        Returns a list of tuples:
        (question_text, option_a, option_b, option_c, option_d, correct_option)
        """
        database_manager.cursor.execute(
            """
            SELECT question_text, option_a, option_b, option_c, option_d, correct_option
            FROM quiz_questions
            WHERE chapter_id = %s
            ORDER BY question_id ASC
            """,
            (chapter_id,),
        )
        return database_manager.cursor.fetchall()

    def fetch_analyze_and_improve_curriculum(self, curriculum_id: int) -> dict:
        """
        (Optional) Fetches progress log reflections, analyzes them using an LLM,
        and suggests curriculum improvements with potential DB modifications.
        """
        # Fetch reflections

        database_manager.cursor.execute(
            """
            SELECT qr.reflection_after_quiz, qr.taken_at, cc.title
            FROM quiz_results qr
            JOIN curriculum_chapters cc ON qr.chapter_id = cc.chapter_id
            WHERE cc.curriculum_id = (
                SELECT curriculum_id FROM curriculum_chapters WHERE chapter_id = %s
            ) 
            AND qr.reflection_after_quiz IS NOT NULL
            ORDER BY qr.taken_at DESC;
            """,
            (curriculum_id,),
        )

        reflections = database_manager.cursor.fetchall()

        if not reflections:
            return {
                "analysis": "No reflections available for this curriculum.",
                "improvements": "No improvements suggested due to lack of data.",
            }

        reflection_details = "\n".join(
            f"Chapter: {title} | Phase: {phase} | Reflection: {reflection}"
            for reflection, phase, _, title in reflections
        )

        # Fetch curriculum for context
        database_manager.cursor.execute(
            """
            SELECT subject, goal_description, learning_goal 
            FROM curriculums 
            WHERE curriculum_id = %s
            """,
            (curriculum_id,),
        )
        curriculum = database_manager.cursor.fetchone()
        if not curriculum:
            return {
                "analysis": "Curriculum not found.",
                "improvements": "No improvements suggested.",
            }

        subject, goal_description, learning_goal = curriculum

        # Prepare prompt
        prompt = f"""
        You are an expert curriculum analyst and instructional designer. 

        The following curriculum exists:
        - Subject: {subject}
        - Goal Description: {goal_description}
        - Learning Goal: {learning_goal}

        The user has provided reflections for each chapter as follows:
        {reflection_details}

        Provide actionable improvements:
        1. Add supplementary resources for difficult topics.
        2. Adjust chapter order or pacing.
        3. Identify redundant chapters to streamline the curriculum.

        Format your response as:
        "improvements": ["suggestion 1", "suggestion 2", ...]
        """

        try:
            # Use the agent
            agent_executor = create_agent_executor()
            response = agent_executor.invoke({"input": prompt})
            structured_response = response.get("output", "").strip()

            # Now fetch all chapters
            database_manager.cursor.execute(
                """
                SELECT chapter_id, title, description, scheduled_date, is_completed
                FROM curriculum_chapters
                WHERE curriculum_id = %s AND is_completed = 'false'
                """,
                (curriculum_id,),
            )
            chapters = database_manager.cursor.fetchall()

            # Prepare chapter details
            chapter_details = "\n".join(
                f"Chapter ID: {chapter_id}, Title: {title}, Description: {description}, "
                f"Scheduled Date: {scheduled_date}, Completed: {is_completed}"
                for chapter_id, title, description, scheduled_date, is_completed in chapters
            )

            modification_prompt = f"""
            You are an expert database administrator and curriculum analyst. 

            The database has the following table structure for `curriculum_chapters`:
            - `chapter_id` (Primary Key, INT)
            - `curriculum_id` (Foreign Key, INT)
            - `title` (VARCHAR(255), NOT NULL)
            - `description` (TEXT)
            - `scheduled_date` (DATE)
            - `is_completed` (BOOLEAN, DEFAULT FALSE)
            - `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

            You have analyzed the curriculum reflections and provided the following improvements:
            {structured_response}

            Here are the existing chapters for the curriculum:
            {chapter_details}

            Based on the reflections and current chapters, suggest changes to the curriculum by generating SQL queries that:
            1. Update existing chapters (e.g., change title, description, or scheduled date).
            2. Delete redundant chapters.
            3. Add new chapters (with appropriate `curriculum_id`, title, description, and scheduled date).

            Format your response as valid SQL statements specific to the `curriculum_chapters` table. 
            Ensure each query respects the database schema.
            """

            modification_response = agent_executor.invoke({"input": modification_prompt})
            modifications = modification_response.get("output", "").strip()

            # Split and execute each SQL statement
            sql_statements = modifications.split(";")
            for statement in sql_statements:
                if statement.strip():
                    database_manager.cursor.execute(statement)
            database_manager.cursor.connection.commit()

            return {
                "analysis": "Reflections analyzed successfully.",
                "improvements": structured_response,
            }

        except Exception as e:
            return {
                "analysis": "Error occurred while processing reflections.",
                "improvements": f"Unable to provide improvements due to an LLM error: {str(e)}",
            }

def get_closest_subject(email: str, subject: str) -> Optional[str]:
    """
    Finds the closest matching subject for a user using fuzzy matching with case-insensitivity.
    Returns the subject with the original case as stored in the DB if a match is found.
    """

    database_manager.cursor.execute(
        """
        SELECT DISTINCT LOWER(subject) AS normalized_subject 
        FROM curriculums 
        WHERE email = %s
        """,
        (email,),
    )
    subjects = [row[0] for row in database_manager.cursor.fetchall()]

    if not subjects:
        return None  # No subjects available for this user

    subject_lower = subject.lower()
    best_match, score = process.extractOne(subject_lower, subjects)
    if score >= 80:
        # Return the original-cased subject from the DB
        database_manager.cursor.execute(
            """
            SELECT subject 
            FROM curriculums 
            WHERE email = %s AND LOWER(subject) = %s
            LIMIT 1
            """,
            (email, best_match),
        )
        original_subject = database_manager.cursor.fetchone()
        
        return original_subject[0] if original_subject else None
    
    return None


def generate_quiz_for_chapter(chapter_id: int, chapter_title: str, chapter_description: str) -> str:
    """
    Generates MCQ questions for the given chapter using the LLM
    and saves them to the database. Returns a status message.
    """
    try:
        llm = get_llm()
        prompt = f"""
        You are an expert quiz creator. Based on the chapter titled "{chapter_title}" with the following description:
        "{chapter_description}"

        Create 6 multiple-choice questions (MCQs) in strict JSON format. Each question must have:
        - Four options: A, B, C, and D.
        - Indicate the correct option (A, B, C, or D).

        The output must be a JSON array of dictionaries like this:
        [
            {{
                "question": "What is the capital of France?",
                "options": ["Paris", "Madrid", "Berlin", "Rome"],
                "correct_option": "A"
            }},
            ...
        ]
        """

        response = llm([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Extract JSON
        match = re.search(r"(\[.*\])", content, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON array found in LLM response.")
        quiz_questions = json.loads(match.group(1))

        # Basic validation
        for question in quiz_questions:
            if (
                "question" not in question
                or "options" not in question
                or len(question["options"]) != 4
                or "correct_option" not in question
                or question["correct_option"] not in ["A", "B", "C", "D"]
            ):
                raise ValueError(f"Invalid question format: {question}")

        # Insert into DB
        for question in quiz_questions:
            database_manager.cursor.execute(
                """
                INSERT INTO quiz_questions (chapter_id, question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    chapter_id,
                    question["question"],
                    question["options"][0],
                    question["options"][1],
                    question["options"][2],
                    question["options"][3],
                    question["correct_option"],
                ),
            )
        database_manager.cursor.connection.commit()

        return f"Quiz created and saved successfully for chapter {chapter_title} (chapter_id={chapter_id})."

    except Exception as e:
        return f"Failed to generate or save quiz for chapter {chapter_id}: {str(e)}"


# Instantiate the handler for external import
curriculum_handler = CurriculumHandler()
