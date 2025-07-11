import os
import json
import redis
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from .celery_worker import generate_audio_task
from pydantic import BaseModel

app = FastAPI(title="Gemini TTS Service")
REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
SETTINGS_KEY = "tts_settings"

def load_settings():
    """טוען הגדרות מ-Redis או ממשתני הסביבה"""
    settings_json = redis_client.get(SETTINGS_KEY)
    if settings_json:
        return json.loads(settings_json)
    else:
        # Fallback to environment variables
        return {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "tts-1"),
            "TTS_VOICE": os.getenv("TTS_VOICE", "echo"),
            "SUCCESS_WEBHOOK_URL": os.getenv("SUCCESS_WEBHOOK_URL", ""),
            "ERROR_WEBHOOK_URL": os.getenv("ERROR_WEBHOOK_URL", "")
        }

class TTSRequest(BaseModel):
    text: str
    phone_number: str

@app.post("/generate-audio")
def queue_audio_generation(request: TTSRequest):
    """מקבל בקשה ומכניס אותה לתור לעיבוד"""
    task = generate_audio_task.delay(text=request.text, phone_number=request.phone_number)
    return {"message": "Task queued successfully", "task_id": task.id}

@app.get("/settings", response_class=HTMLResponse)
async def get_settings_page():
    """מציג את דף ההגדרות עם הערכים הנוכחיים"""
    settings = load_settings()
    # כאן הקוד של ה-HTML נשאר זהה לקוד מהתשובה הקודמת
    html_content = f"""
    <html>
        <head>
            <title>Settings</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                form {{ display: flex; flex-direction: column; max-width: 500px; }}
                label {{ margin-top: 10px; }}
                input, select {{ padding: 8px; margin-top: 5px; }}
                button {{ margin-top: 20px; padding: 10px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <h1>Settings</h1>
            <form action="/settings" method="post">
                <label for="gemini_api_key">Gemini API Key:</label>
                <input type="password" id="gemini_api_key" name="gemini_api_key" value="{settings.get('GEMINI_API_KEY', '')}">

                <label for="gemini_model">Gemini Model (e.g., tts-1, gemini-1.5-pro):</label>
                <input type="text" id="gemini_model" name="gemini_model" value="{settings.get('GEMINI_MODEL', 'tts-1')}">

                <label for="tts_voice">TTS Voice:</label>
                <input type="text" id="tts_voice" name="tts_voice" value="{settings.get('TTS_VOICE', 'echo')}">
                
                <label for="success_webhook_url">Success Webhook URL:</label>
                <input type="text" id="success_webhook_url" name="success_webhook_url" value="{settings.get('SUCCESS_WEBHOOK_URL', '')}">
                
                <label for="error_webhook_url">Error Webhook URL:</label>
                <input type="text" id="error_webhook_url" name="error_webhook_url" value="{settings.get('ERROR_WEBHOOK_URL', '')}">

                <button type="submit">Save Settings</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/settings")
async def save_settings_to_redis(request: Request):
    """שומר את ההגדרות מהטופס ל-Redis"""
    form_data = await request.form()
    settings = {
        "GEMINI_API_KEY": form_data.get("gemini_api_key"),
        "GEMINI_MODEL": form_data.get("gemini_model"),
        "TTS_VOICE": form_data.get("tts_voice"),
        "SUCCESS_WEBHOOK_URL": form_data.get("success_webhook_url"),
        "ERROR_WEBHOOK_URL": form_data.get("error_webhook_url")
    }
    redis_client.set(SETTINGS_KEY, json.dumps(settings))
    return RedirectResponse(url="/settings", status_code=303)