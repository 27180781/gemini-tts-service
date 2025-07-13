import os
import json
import redis
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from .celery_worker import generate_audio_task
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Gemini TTS Service")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
SETTINGS_KEY = "tts_settings"

def load_settings():
    """Loads settings from Redis or environment variables."""
    settings_json = redis_client.get(SETTINGS_KEY)
    if settings_json:
        return json.loads(settings_json)
    else:
        # Default settings pointing to the new models
        return {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "GEMINI_TTS_MODEL": os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
            "TTS_VOICE": os.getenv("TTS_VOICE", "Kore"),
            "TTS_PROMPT": os.getenv("TTS_PROMPT", ""),
            "SUCCESS_WEBHOOK_URL": os.getenv("SUCCESS_WEBHOOK_URL", ""),
            "ERROR_WEBHOOK_URL": os.getenv("ERROR_WEBHOOK_URL", ""),
            "CALLBACK_URL": os.getenv("CALLBACK_URL", ""),
            # --- ⬇️ שדות חדשים עבור פרמטרים ⬇️ ---
            "CALLBACK_TOKEN": os.getenv("CALLBACK_TOKEN", ""),
            "CALLBACK_WITH_SMS": os.getenv("CALLBACK_WITH_SMS", "1"),
            "CALLBACK_TTS_MODE": os.getenv("CALLBACK_TTS_MODE", "1"),
        }

class TTSRequest(BaseModel):
    text: str
    phone_number: str
    short_text: Optional[str] = None

@app.post("/generate-audio")
def queue_audio_generation(request: TTSRequest):
    """Queues a task for audio generation and callback."""
    task = generate_audio_task.delay(
        text=request.text,
        phone_number=request.phone_number,
        short_text=request.short_text
    )
    return {"message": "Task queued successfully", "task_id": task.id}

@app.get("/settings", response_class=HTMLResponse)
async def get_settings_page():
    """Displays the settings page."""
    settings = load_settings()
    html_content = f"""
    <html>
        <head>
            <title>Settings</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; direction: rtl; text-align: right; }}
                h1 {{ text-align: center; }}
                form {{ display: flex; flex-direction: column; max-width: 600px; margin: auto; }}
                label {{ margin-top: 15px; font-weight: bold; }}
                input, select {{ padding: 10px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }}
                button {{ margin-top: 25px; padding: 12px; cursor: pointer; background-color: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; }}
                .help-text {{ font-size: 0.9em; color: #666; margin-top: 2px; }}
                code {{ background-color: #f1f1f1; padding: 2px 4px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>הגדרות מערכת TTS</h1>
            <form action="/settings" method="post">
                <label for="api_key">Gemini API Key:</label>
                <input type="password" id="api_key" name="api_key" value="{settings.get('GEMINI_API_KEY', '')}">

                <label for="tts_model">Gemini TTS Model:</label>
                <input type="text" id="tts_model" name="tts_model" value="{settings.get('GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')}">
                <div class="help-text">מודלים מומלצים: gemini-2.5-flash-preview-tts</div>

                <label for="tts_voice">TTS Voice:</label>
                <input type="text" id="tts_voice" name="tts_voice" value="{settings.get('TTS_VOICE', 'Kore')}">
                
                <label for="tts_prompt">סגנון הקראה (הנחיה):</label>
                <input type="text" id="tts_prompt" name="tts_prompt" value="{settings.get('TTS_PROMPT', '')}">

                <label for="success_webhook_url">Success Webhook URL (for Audio File):</label>
                <input type="url" id="success_webhook_url" name="success_webhook_url" value="{settings.get('SUCCESS_WEBHOOK_URL', '')}">
                <div class="help-text">תומך ב-<code>{{PHONE_NUMBER}}</code></div>

                <label for="error_webhook_url">Error Webhook URL:</label>
                <input type="url" id="error_webhook_url" name="error_webhook_url" value="{settings.get('ERROR_WEBHOOK_URL', '')}">

                <label for="callback_url">Callback Base URL:</label>
                <input type="url" id="callback_url" name="callback_url" value="{settings.get('CALLBACK_URL', '')}">
                <div class="help-text">רק כתובת הבסיס, ללא פרמטרים. למשל: https://www.call2all.co.il/ym/api/RunCampaign</div>

                <label for="callback_token">Callback Token:</label>
                <input type="text" id="callback_token" name="callback_token" value="{settings.get('CALLBACK_TOKEN', '')}">

                <label for="callback_with_sms">Callback 'withSMS' Parameter:</label>
                <input type="text" id="callback_with_sms" name="callback_with_sms" value="{settings.get('CALLBACK_WITH_SMS', '1')}">

                <label for="callback_tts_mode">Callback 'ttsMode' Parameter:</label>
                <input type="text" id="callback_tts_mode" name="callback_tts_mode" value="{settings.get('CALLBACK_TTS_MODE', '1')}">

                <button type="submit">שמור הגדרות</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/settings")
async def save_settings_to_redis(request: Request):
    """Saves settings from the form to Redis."""
    form_data = await request.form()
    settings = {
        "GEMINI_API_KEY": form_data.get("api_key"),
        "GEMINI_TTS_MODEL": form_data.get("tts_model"),
        "TTS_VOICE": form_data.get("tts_voice"),
        "TTS_PROMPT": form_data.get("tts_prompt"),
        "SUCCESS_WEBHOOK_URL": form_data.get("success_webhook_url"),
        "ERROR_WEBHOOK_URL": form_data.get("error_webhook_url"),
        "CALLBACK_URL": form_data.get("callback_url"),
        # --- ⬇️ שמירת השדות החדשים ⬇️ ---
        "CALLBACK_TOKEN": form_data.get("callback_token"),
        "CALLBACK_WITH_SMS": form_data.get("callback_with_sms"),
        "CALLBACK_TTS_MODE": form_data.get("callback_tts_mode"),
    }
    redis_client.set(SETTINGS_KEY, json.dumps(settings))
    return RedirectResponse(url="/settings", status_code=303)