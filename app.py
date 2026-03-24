from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import math
from fastapi.responses import HTMLResponse
import webbrowser

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# API KEY (keep yours)
# -----------------------------
API_KEY = "api_key_here"

# -----------------------------
# DATA MODEL
# -----------------------------
class UserProfile(BaseModel):
    age: int
    income: float
    expenses: float
    savings: float
    investments: float
    debt: float
    emi: float
    insurance: str
    risk: str
    retireAge: int

# -----------------------------
# LOGIC (from logic.py)
# -----------------------------
def calculate_score(p):
    scores = {}

    months = p.savings / max(p.expenses, 1)
    scores["emergency"] = 100 if months >= 6 else 70 if months >= 3 else 40

    ratio = p.emi / max(p.income, 1)
    scores["debt"] = 100 if ratio < 0.3 else 60 if ratio < 0.5 else 30

    rate = p.investments / max(p.income, 1)
    scores["savings"] = 100 if rate >= 0.2 else 60 if rate >= 0.1 else 30

    scores["insurance"] = 100 if p.insurance == "both" else 50
    scores["investment"] = 80 if rate >= 0.15 else 50
    scores["retirement"] = 70 if p.savings > 200000 else 40

    total = sum(scores.values()) // len(scores)

    return {"total": total, "breakdown": scores}


def calculate_fire(p):
    years = p.retireAge - p.age
    r = 0.12 / 12
    n = years * 12

    sip = p.investments

    fv = sip * ((1 + r)**n - 1) / r
    lump = p.savings * (1.12 ** years)

    total = fv + lump

    return {"years": years, "corpus": round(total, 2)}

# -----------------------------
# AI CHAT (from ai.py)
# -----------------------------
def financial_agent(query, profile, mode="chat"):
    try:
        prompt = f"""
You are a financial advisor.

User:
Income: ₹{profile.get('income')}
Expenses: ₹{profile.get('expenses')}
Savings: ₹{profile.get('savings')}

{ "Give 4 short suggestions." if mode=="suggestions" else f"Answer: {query}" }
"""

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-70b-8192",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        data = response.json()

        # 🔥 PRINT FULL RESPONSE (VERY IMPORTANT)
        print("FULL API RESPONSE:", data)

        # ✅ SAFE CHECK
        if "choices" not in data:
            return f"API Error: {data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI ERROR:", e)
        return "AI failed. Check backend."
# -----------------------------
# ROUTES
# -----------------------------
@app.post("/analyze")
def analyze(profile: UserProfile):
    score_data = calculate_score(profile)
    fire_data = calculate_fire(profile)

    suggestions_text = financial_agent(
        query="",
        profile=profile.dict(),
        mode="suggestions"
    )

    suggestions = [
        s.strip("-• ")
        for s in suggestions_text.split("\n")
        if s.strip()
    ]

    return {
        "score": score_data,
        "fire": fire_data,
        "suggestions": suggestions
    }

@app.post("/chat")
def chat(data: dict):
    message = data.get("message")
    profile = data.get("profile")

    reply = financial_agent(
        query=message,
        profile=profile,
        mode="chat"
    )

    return {"reply": reply}
# -----------------------------
# SERVE FRONTEND
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    with open("fire_advisor_updated.html", "r", encoding="utf-8") as f:
        return f.read()
    
# auto open browser
@app.on_event("startup")
def open_browser():
    webbrowser.open("http://localhost:8000")