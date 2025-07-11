from fastapi import FastAPI
from pydantic import BaseModel
from .celery_worker import generate_audio_task

app = FastAPI(title="Gemini TTS Service")

class TTSRequest(BaseModel):
    text: str
    phone_number: str

@app.post("/generate-audio")
def queue_audio_generation(request: TTSRequest):
    """
    Receives a request and puts it in the queue for processing.
    Returns a task ID immediately.
    """
    task = generate_audio_task.delay(text=request.text, phone_number=request.phone_number)
    return {"message": "Task queued successfully", "task_id": task.id}

@app.get("/health")
def health_check():
    return {"status": "ok"}