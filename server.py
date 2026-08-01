import sqlite3
import requests
from fastapi import FastAPI
from duckduckgo_search import DDGS

app = FastAPI()
DB_FILE = "chat_history.db"

# Инициализация базы данных
conn = sqlite3.connect(DB_FILE)
conn.execute('''CREATE TABLE IF NOT EXISTS messages 
             (id INTEGER PRIMARY KEY, user_id TEXT, role TEXT, content TEXT)''')
conn.commit()
conn.close()

def save_msg(user_id, role, content):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_history(user_id, limit=6):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

@app.get("/ask")
def ask_ai(query: str, user_id: str = "papa"):
    print(f"\n[Вопрос]: {query}")
    
    # 1. Поиск в интернете через DuckDuckGo
    search_context = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=2))
            if results:
                search_context = "\n".join([f"{r['title']}: {r['body']}" for r in results])
    except Exception:
        pass
    
    user_content = query
    if search_context:
        user_content += f"\n\nСправка из интернета:\n{search_context}"
        
    save_msg(user_id, "user", user_content)
    
    # 2. Обращение к бесплатной нейросети (без платных моделей)
    history = get_history(user_id)
    sys_prompt = {"role": "system", "content": "Ты умный и вежливый помощник. Отвечай на русском языке. Используй справку из интернета, если она есть."}
    
    messages = [sys_prompt] + history
    
    try:
        # Убрали "model": "openai" — теперь запрос 100% бесплатный
        response = requests.post(
            "https://text.pollinations.ai/",
            json={"messages": messages},
            timeout=30
        )
        bot_reply = response.text.strip()
    except Exception as e:
        bot_reply = "Извините, произошла ошибка связи с нейросетью."
    
    save_msg(user_id, "assistant", bot_reply)
    return {"reply": bot_reply}

@app.get("/clear")
def clear_db(user_id: str = "papa"):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "Очищено"}
