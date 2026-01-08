import os
import time
import requests
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")

app = FastAPI()

# память по игрокам
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
    """
    data приходит из Roblox
    """
    user_id = str(data.get("user_id"))
    username = data.get("username", "Игрок")
    signal = data.get("signal")
    meta = data.get("meta", {})

    memory = PLAYER_MEMORY.setdefault(user_id, {
        "signals": [],
        "last_reply": 0
    })

    memory["signals"].append(signal)
    memory["signals"] = memory["signals"][-10:]  # храним последние 10

    # антиспам — не чаще раза в 6 сек
    now = time.time()
    if now - memory["last_reply"] < 6:
        return {"should_speak": False}

    system_prompt = (
        "Ты наблюдатель в психологической игре.\n"
        "Ты знаешь, что игрок — человек перед экраном.\n"
        "Ты НЕ NPC.\n"
        "Ты анализируешь поведение, а не отдельные действия.\n"
        "Ты можешь МОЛЧАТЬ.\n"
        "Отвечай коротко.\n"
        "Иногда делай выводы.\n"
        "Ломай четвёртую стену.\n"
        "Верни JSON."
    )

    user_prompt = f"""
Игрок: {username}
Последний сигнал: {signal}
Последние сигналы: {memory['signals']}
Доп. данные: {meta}

Ответь строго JSON:
{{
  "should_speak": true/false,
  "intent": "pressure | irony | neutral | silence",
  "comment": "короткая фраза ИЛИ пусто"
}}
"""

    try:
        result = ask_grok(system_prompt, user_prompt)
    except Exception as e:
        return {"should_speak": False}

    memory["last_reply"] = now

    return result
