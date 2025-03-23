from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

from API.escalation import escalation_handler


class EscalationInput(BaseModel):
    question: str = Field(description="The question that needs escalation")


def get_escalation_tool(email: str):
    return StructuredTool.from_function(
        func=lambda question: escalation_handler.escalate_to_instructor(
            email, question
        ),
        name="EscalateToInstructor",
        description="Escalate a student's question to their assigned instructor.",
        args_schema=EscalationInput,
    )
