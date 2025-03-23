from tools.StartQuiz import get_start_quiz_tool
from tools.PdfToCourse import get_pdftocourse_tool
from tools.Escalation import get_escalation_tool
from tools.GetTodayDate import get_today_date_tool
from tools.GetEnrollment import get_enrollment_tool
from tools.ScrapeWebsite import get_scrape_website_tool
from tools.StudyIntention import get_study_intention_tool
from tools.ContinueCourse import get_continue_course_tool
from tools.ScheduledChapters import get_scheduled_chapters_tool
from tools.GetPastMessages import get_past_messages_tool
from tools.PdfToContext import get_upload_pdfs_tool
from tools.GetCourseContext import get_course_context_tool

def build_agent_tools(email, on_continue_course):
    """
    Builds and returns the list of Tools to be passed to the agent.
    """
    return [
        get_past_messages_tool(email=email),
        get_enrollment_tool(email=email),
        get_study_intention_tool(email=email),
        get_today_date_tool(),
        get_continue_course_tool(email=email, on_continue_course=on_continue_course),
        get_scrape_website_tool(),
        get_escalation_tool(email=email),
        get_start_quiz_tool(email=email),
        get_pdftocourse_tool(),
        get_scheduled_chapters_tool(email=email),
        get_upload_pdfs_tool(),
        get_course_context_tool(email=email),
    ]
