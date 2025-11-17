from pydantic import BaseModel

class LLM_Request(BaseModel):
    request: str