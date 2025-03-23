from typing import Callable, Optional
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from API.curriculum import curriculum_handler


class ContinueCourseInput(BaseModel):
    subject: str = Field(
        description="The subject of the course the user wants to continue"
    )


def get_continue_course_tool(
    email: str,
    on_continue_course: Optional[Callable[[str, str, str], None]] = None,
):
    return StructuredTool.from_function(
        func=lambda subject: curriculum_handler.get_next_chapter_to_learn(
            email, subject, on_continue_course
        ),
        name="ContinueCourse",
        description="Use when user wants to continue or start on their enrolled course",
        args_schema=ContinueCourseInput,
    )
