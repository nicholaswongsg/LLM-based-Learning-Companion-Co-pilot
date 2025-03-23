from langchain.tools import StructuredTool

from API.curriculum import curriculum_handler


def get_enrollment_tool(email: str):
    return StructuredTool.from_function(
        func=lambda: curriculum_handler.get_current_enrollment(email),
        name="GetCurrentEnrollment",
        description="Use to find out what course the user is currently enrolled in",
    )
