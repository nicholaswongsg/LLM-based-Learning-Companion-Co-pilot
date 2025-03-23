from langchain.tools import StructuredTool

from API.chapter import chapter_handler


def get_scheduled_chapters_tool(email: str):
    return StructuredTool.from_function(
        func=lambda: chapter_handler.get_scheduled_chapters(email),
        name="FetchScheduledChapters",
        description="Fetch today's date and the user's scheduled chapters.",
        return_direct=False,
    )
