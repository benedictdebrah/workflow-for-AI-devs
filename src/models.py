from pydantic import BaseModel
from typing import List

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    bot_response: str
    chat_history: List[dict]