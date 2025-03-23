from langchain_openai import AzureChatOpenAI
from typing import Optional, List
from langchain.callbacks.base import BaseCallbackHandler


def get_llm(streaming: bool = False, callbacks: Optional[List[BaseCallbackHandler]] = None):
    return AzureChatOpenAI(
        temperature=0,
        top_p=0,
        azure_deployment="gpt-4o",
        streaming=streaming,
        callbacks=callbacks,
    )


def get_llm_fast(streaming: bool = False, callbacks: Optional[List[BaseCallbackHandler]] = None):
    return AzureChatOpenAI(
        temperature=0,
        top_p=0,
        azure_deployment="gpt-4o-mini",
        streaming=streaming,
        callbacks=callbacks,
    )
