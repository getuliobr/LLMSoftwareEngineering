from fastapi import FastAPI, Request
from main import main_function
from models import LLM_Request

app = FastAPI()

@app.post("/get_infos")
async def get_infos(request: LLM_Request):
    question = request.request
    final_answer = main_function(question)
    return {"answer": final_answer}