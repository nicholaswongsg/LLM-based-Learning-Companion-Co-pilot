import os
import numpy as np
from Azure.Search import client

def get_embedding(text):
    """
    Fetches embedding for a given text using Azure OpenAI.
    """
    try:
        if not isinstance(text, str):
            text = str(text)

        response = client.embeddings.create(
            input=text,
            model=os.getenv("TEXT_EMBEDDING_MODEL_NAME")
        )

        if response and response.data:
            return np.array(response.data[0].embedding)
        else:
            print("Azure OpenAI returned empty response.")
            return np.zeros(1536)

    except Exception as e:
        print(f"Error getting embedding from Azure OpenAI: {e}")
        return np.zeros(1536)
