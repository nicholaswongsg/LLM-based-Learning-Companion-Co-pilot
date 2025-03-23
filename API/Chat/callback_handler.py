import streamlit as st
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any
import json

class StreamlitCallbackHandler(BaseCallbackHandler):
    def __init__(self, container: st.delta_generator.DeltaGenerator):
        # Placeholder for streaming tokens
        self.container = container
        self.placeholder = self.container.empty()
        self.token_buffer = ""
        self.is_json_detected = False  # Flag to prevent JSON streaming

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        # Accumulate tokens
        self.token_buffer += token

        # Detect JSON start
        if self.token_buffer.strip().startswith("{"):
            self.is_json_detected = True

        # Suppress rendering JSON-like content
        if not self.is_json_detected:
            self.placeholder.markdown(self.token_buffer)

    def get_final_text(self) -> str:
        # Return the fully accumulated response
        return self.token_buffer
