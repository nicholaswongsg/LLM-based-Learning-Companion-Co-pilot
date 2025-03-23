from langchain.tools import StructuredTool

from utils.date_utils import get_today_date


def get_today_date_tool():
    return StructuredTool.from_function(
        func=get_today_date,
        name="GetTodayDate",
        description="Use to get today's date in YYYY-MM-DD format",
        return_direct=False,
    )
