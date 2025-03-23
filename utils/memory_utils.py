import time
from langchain.memory import ConversationBufferMemory

def get_user_memory(user_memories: dict, email: str):
    """
    Retrieve or create memory for the given email, update last active timestamp.
    """
    if email not in user_memories:
        user_memories[email] = {
            "memory": ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            ),
            "last_active": time.time(),
        }
    else:
        user_memories[email]["last_active"] = time.time()

    return user_memories[email]["memory"]
