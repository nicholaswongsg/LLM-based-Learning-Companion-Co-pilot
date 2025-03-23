from langchain.callbacks.base import BaseCallbackHandler
from API.chapter import chapter_handler
from tools.GetCourseContext import get_course_context_tool

def build_initial_context(email: str, summarized_feedback: str, user_input: str):
    """
    Builds a context for first-time user queries based on scheduled chapters, date, and feedback.
    """
    scheduled_chapters = chapter_handler.get_scheduled_chapters(email)
    today_date = scheduled_chapters.get("today_date", "")
    chapters = scheduled_chapters.get("scheduled_chapters", [])

    if chapters:
        # Group chapters by subject
        chapters_by_subject = {}
        for chapter in chapters:
            subject = chapter["subject"]
            chapters_by_subject.setdefault(subject, []).append(chapter)

        subjects_context = "\n".join([
            f"- {subj} ({chapters_by_subject[subj][0]['title']})"
            for subj in chapters_by_subject.keys()
        ])

        reminder_context = f"""
        **Summarized Feedback:**
        {summarized_feedback}

        **Today's Date:** {today_date}
        **Available Subjects:**
        {subjects_context}

        Return subjects_context as it is because it contains the course name 
        and chapter they last stop. Encourage them to continue their learning journey.

        **User Query**
        {user_input}
        """
    else:
        reminder_context = f"""
        **Summarized Feedback:**
        {summarized_feedback}

        User doesn't have any scheduled chapters for today. 
        Encourage them to continue their learning journey.
        **User Query**
        {user_input}
        """
    return reminder_context
