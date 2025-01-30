from prefect import task, flow
from fastapi import HTTPException
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
import os
from models import ChatRequest, ChatResponse

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
GROQ_API_KEY = os.getenv("GROQ_API")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["fingertips"]
messages_collection = db["sessions"]

groq_model = ChatGroq(model="llama3-8b-8192", api_key=GROQ_API_KEY)

@task
def process_chat(chat_request: ChatRequest):
    user_id = chat_request.user_id
    user_message = chat_request.message

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ API key is missing.")

    # Fetch chat history for the user
    chat_history = list(messages_collection.find({"user_id": user_id}, {"_id": 0}))

    # Generate a response using the GROQ model
    try:
        input_messages = [HumanMessage(content=user_message)]
        if chat_history:
            input_messages = [
                HumanMessage(content=msg["user_message"]) if msg["role"] == "user"
                else AIMessage(content=msg["bot_message"])
                for msg in chat_history
            ]
            input_messages.append(HumanMessage(content=user_message))

        response = groq_model.invoke(input_messages)
        bot_response = response.content

        # Save user message and bot response in MongoDB
        messages_collection.insert_one({"user_id": user_id, "role": "user", "user_message": user_message})
        messages_collection.insert_one({"user_id": user_id, "role": "bot", "bot_message": bot_response})

        # Fetch updated chat history
        updated_chat_history = list(messages_collection.find({"user_id": user_id}, {"_id": 0}))

        return ChatResponse(bot_response=bot_response, chat_history=updated_chat_history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


@flow
def chat_flow():
    chat_request = ChatRequest(user_id="example_user", message="Hello, how are you?")
    process_chat(chat_request)
    
if __name__ == "__main__":
    chat_flow()


