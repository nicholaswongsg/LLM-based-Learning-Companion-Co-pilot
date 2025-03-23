from typing import List, Optional
from langchain.tools import StructuredTool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.callbacks.base import BaseCallbackHandler
from langchain.memory import ConversationBufferMemory

from utils.llm_utils import get_llm
from tools.GetTodayDate import get_today_date_tool


def create_agent_executor(
    prompt: str = "",
    memory: Optional[ConversationBufferMemory] = None,
    tools: List[StructuredTool] = [get_today_date_tool()],
    callbacks: Optional[List[BaseCallbackHandler]] = None,
    streaming: bool = False,
):
    """
    Create and return an AgentExecutor with support for streaming and callbacks.

    Args:
        prompt (str): System message prompt template to initialize the agent.
        memory (ConversationBufferMemory, optional): Memory for the conversation.
        tools (List[StructuredTool], optional): Tools the agent can call.
        callbacks (List[BaseCallbackHandler], optional): Callbacks to handle streaming tokens/events.
        streaming (bool, optional): Whether to enable token streaming for the LLM.

    Returns:
        AgentExecutor: Configured agent executor.
    """
    # IMPORTANT: Actually pass `streaming` and `callbacks` to get_llm()
    llm = get_llm(streaming=streaming, callbacks=callbacks)

    # Build the agent that can call tools
    agent = create_tool_calling_agent(
        llm=llm,
        tools=tools,
        prompt=ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(prompt),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                HumanMessagePromptTemplate.from_template("{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        ),
    )

    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        input_key="input",
        output_key="output",
        verbose=True,
    )
    return agent_executor
