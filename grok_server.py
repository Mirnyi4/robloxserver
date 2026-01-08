import os
import time
import json
import requests
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")

app = FastAPI()

PLAYER_MEMORY = {}

def ask_grok(system_prompt, user_prompt):
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "grok-3-latest",
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    r = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


@app.post("/observe")
def observe(data: dict):
    user_id = str(data.get("user_id"))
    username = data.get("username", "Игрок")
    signals = data.get("signals", [])

    memory = PLAYER_MEMORY.setdefault(user_id, {
        "signals": [],
        "last_reply": 0
    })

    for s in signals:
        memory["signals"].append(s)

    memory["signals"] = memory["signals"][-8:]

    now = time.time()
    if now - memory["last_reply"] < 6:
        return {"should_speak": False}

    system_prompt = (
        "Ты наблюдатель в психологической игре.\n"
        "Ты знаешь, что игрок — человек.\n"
        "Ты ломаешь четвёртую стену.\n"
        "Ты можешь молчать.\n"
        "Отвечай кратко.\n"
        "Верни СТРОГО JSON."
    )

    user_prompt = f"""
Игрок: {username}
Последние сигналы: {memory['signals']}

Ответь строго JSON:
{{
  "should_speak": true/false,
  "intent": "irony | pressure | neutral | silence",
  "comment": "короткая фраза или пусто"
}}
"""

    try:
        raw = ask_grok(system_prompt, user_prompt)
        parsed = json.loads(raw)
    except Exception:
        return {"should_speak": False}

    memory["last_reply"] = now
    return parsed
