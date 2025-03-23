import time
import tiktoken
import threading
import os
import streamlit as st

from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory

from DB.index import database_manager
from Azure.Search import search_client, client
from API.chapter import chapter_handler
from API.feedback import FeedbackHandler
from API.Chat.constant import CHAT_PROMPT

import numpy as np
from agent import create_agent_executor

from utils.feedback_utils import fetch_and_summarize_feedback
from utils.agent_utils import build_agent_tools
from utils.memory_utils import get_user_memory
from utils.context_utils import build_initial_context

from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, Optional

class ChatHandler:
    def __init__(self):
        print("ChatHandler initialized!")
        self.user_memories = {}  # {email: {"memory": ConversationBufferMemory, "last_active": timestamp}}
        self.search_client = search_client  # For direct vector search if needed
        self.feedback_handler = FeedbackHandler()

        self.cleanup_interval = 300  # Clean inactive users every 5 minutes
        threading.Thread(target=self.__auto_clean_inactive_users, daemon=True).start()

    def clean_inactive_users(self, timeout: int = 3600):
        """
        Removes memory for users inactive for more than `timeout` seconds.
        """
        current_time = time.time()
        to_remove = [
            email for email, data in self.user_memories.items()
            if current_time - data["last_active"] > timeout
        ]
        for email in to_remove:
            del self.user_memories[email]
            print(f"[INFO] Removed inactive user: {email}")

    def handle_feedback(self, email: str, conversation_id: str, feedback_text: str):
        """
        Save user feedback and refresh summarized feedback in memory.
        """
        self.feedback_handler.save_feedback(email, conversation_id, feedback_text)

        summarized_feedback = fetch_and_summarize_feedback(email)
        if email in self.user_memories:
            self.user_memories[email]["summarized_feedback"] = summarized_feedback
            print(f"[INFO] Updated summarized feedback for {email}: {summarized_feedback}")
        else:
            print(f"[WARN] No active session for {email}, summarized feedback not stored in memory.")

    def __auto_clean_inactive_users(self):
        while True:
            self.clean_inactive_users()
            time.sleep(self.cleanup_interval)

    def __trim_chat_history_to_fit_token_limit(self, messages, max_tokens=3000, model_encoding="o200k_base"):
        """
        Trims chat history from the oldest messages to fit within `max_tokens`.
        """
        encoding = tiktoken.get_encoding(model_encoding)
        trimmed_messages = []
        total_tokens = 0

        # Iterate backward (most recent -> oldest)
        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                msg_text = f"{role}: {content}"
            else:
                msg_text = str(msg)

            tokens_count = len(encoding.encode(msg_text))
            if total_tokens + tokens_count > max_tokens:
                break

            trimmed_messages.append(msg)
            total_tokens += tokens_count

        trimmed_messages.reverse()
        return trimmed_messages
    
    def _vector_search_and_refine(
        self, 
        user_input: str, 
        initial_response: str,
        pdf_context: str,
        email: str,
        agent_executor,
        callback_handler: BaseCallbackHandler
    ):
        """
        (Optional) Perform a vector search on user_input to retrieve relevant docs,
        then feed them back to the LLM to produce a refined answer.
        """
        combined_context = f"{initial_response}\n\n📚 **Additional Context from PDFs**:\n{pdf_context}"

        # Reinvoke the agent to refine the answer using combined_context
        refinement_prompt = f"""
        The user asked: {user_input}
        You answered: {initial_response}
        Additional PDF context: {pdf_context}

        Using the above context, refine or update your answer if necessary.
        """

        refined_output = agent_executor.invoke({"input": refinement_prompt})

        if isinstance(refined_output, dict) and "output" in refined_output:
            final_text = refined_output["output"]
        elif isinstance(refined_output, str):
            final_text = refined_output
        elif hasattr(callback_handler, "get_final_text"):
            final_text = callback_handler.get_final_text()
        else:
            final_text = str(refined_output)

        return final_text

    def conversational_rag_stream(
        self, 
        email: str, 
        user_input: str, 
        callback_handler: BaseCallbackHandler
    ):
        """
        A streaming method that uses 'callback_handler' to stream tokens in real time.
        Returns (final_text, conversation_id).
        """
        try:
            memory = get_user_memory(self.user_memories, email)
            # Check Streamlit session state to see if feedback was updated
            feedback_updated = False
            try:
                feedback_updated = st.session_state.pop("feedback_updated", False)
            except ImportError:
                pass  # In non-streamlit context, skip safely
            
            session_data = self.user_memories.get(email, {})
            # Only fetch summarized_feedback if feedback was updated or absent
            if feedback_updated or "summarized_feedback" not in session_data:
                summarized_feedback = fetch_and_summarize_feedback(email)
                session_data["summarized_feedback"] = summarized_feedback
                self.user_memories[email] = session_data
                print(f"[INFO] Summarized feedback refreshed for {email}: {summarized_feedback}")
            else:
                summarized_feedback = session_data["summarized_feedback"]
                print(f"[INFO] Using cached summarized feedback for {email}")

            def on_continue_course(subject: str, chapter_id: str, generated_content):
                memory.save_context(
                    {"input": f"Get next chapter for {subject}, chapter_id: {chapter_id}."},
                    {"output": generated_content},
                )
            
            # Trim chat history before forming the prompt
            memory.chat_memory.messages = self.__trim_chat_history_to_fit_token_limit(
                memory.chat_memory.messages, max_tokens=128000  # GPT-4o's max tokens
            )

            # Prepare the Tools and Agent Executor
            tools = build_agent_tools(email, on_continue_course)
            agent_executor = create_agent_executor(
                prompt=CHAT_PROMPT,
                memory=memory,
                tools=tools,
                callbacks=[callback_handler],
                streaming=True
            )

            # If it's the first message...
            if not memory.chat_memory.messages:
                context = build_initial_context(email, summarized_feedback, user_input)
                response = agent_executor.invoke({"input": context})
            else:
                print("summarized_feedback: ", summarized_feedback)
                # Trim user query if necessary
                encoding = tiktoken.encoding_for_model("gpt-4o")
                user_query_tokens = len(encoding.encode(user_input))

                if user_query_tokens > 128000:
                    print(f"[WARN] User query exceeds token limit. Trimming...")
                    user_input = encoding.decode(encoding.encode(user_input)[:128000])

                # For subsequent messages, just append summarized feedback
                combined_input = f"""
                **Summarized Feedback:**
                {summarized_feedback}

                **User Query**
                {user_input}
                """
                response = agent_executor.invoke({"input": combined_input})

            # Extract full_response from agent
            if isinstance(response, dict) and "output" in response:
                full_response = response["output"]
            elif isinstance(response, str):
                full_response = response
            elif hasattr(callback_handler, "get_final_text"):
                full_response = callback_handler.get_final_text()
            else:
                full_response = str(response)

            # Save conversation in DB
            conversation_id = database_manager.save_message(email, user_input, full_response)
            return full_response, conversation_id

        except Exception as e:
            error_message = f"Error during streaming RAG processing: {e}"
            print(error_message)
            return f"Error: {error_message}", None, None


# Instantiate the handler
chat_handler = ChatHandler()
