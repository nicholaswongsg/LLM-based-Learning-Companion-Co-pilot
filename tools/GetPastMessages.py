from langchain.tools import StructuredTool
from langchain.schema import HumanMessage, AIMessage
from Azure.Search import search_client

def get_past_messages_tool(email: str):
    def fetch_past_messages(query: str, limit: int = 10):
        try:
            print(f"Retrieving past messages for email: {email}, query: {query}")

            # Perform the search using the SearchClient
            results = search_client.search(
                search_text=query,
                filter=f"email eq '{email}'",
                search_fields=["question", "response"],
                select=["question", "response"],
                top=limit,
            )

            # Parse the search results
            past_messages = []
            for result in results:
                if "question" in result and "response" in result:
                    past_messages.append(HumanMessage(content=str(result["question"])))
                    past_messages.append(AIMessage(content=str(result["response"])))

            return past_messages

        except Exception as e:
            print(f"Error retrieving past messages: {e}")
            return []

    # Create and return the tool
    return StructuredTool.from_function(
        func=fetch_past_messages,
        name="GetPastMessages",
        description=(
            "Use this tool to retrieve past messages relevant to the current input. "
            "Provide the user's query as input to get relevant past interactions."
        ),
    )