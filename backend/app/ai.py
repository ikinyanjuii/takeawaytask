import json, os, re
from typing import Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

THEME_RULES = {
    "Notifications & alerts": ["notify", "notification", "alert", "remind", "email", "teams", "slack"],
    "Reporting & analytics": ["report", "dashboard", "analytics", "export", "metric", "chart"],
    "Integrations & APIs": ["integration", "api", "webhook", "sync", "connect", "connector"],
    "Access & permissions": ["permission", "role", "access", "login", "sso", "authentication"],
    "Workflow automation": ["automate", "workflow", "approval", "task", "assign", "manual"],
    "Performance & reliability": ["slow", "performance", "latency", "reliable", "uptime", "timeout"],
}

def _fallback_analysis(title: str, description: str, segment: str) -> dict[str, Any]:
    text = f"{title} {description}".lower()
    theme = max(THEME_RULES, key=lambda k: sum(w in text for w in THEME_RULES[k]))
    if not any(w in text for words in THEME_RULES.values() for w in words):
        theme = "General product experience"
    need = re.sub(r"\\s+", " ", description).strip()
    need = need[:260] + ("…" if len(need) > 260 else "")
    impact = "High" if any(w in text for w in ["blocked", "revenue", "critical", "compliance", "daily"]) else "Medium"
    urgency = "High" if any(w in text for w in ["urgent", "critical", "compliance", "production", "blocked"]) else "Medium"
    return {"underlying_need": need, "theme": theme, "impact": impact, "urgency": urgency, "confidence": 0.62,
            "rationale": f"Rule-based analysis identified {theme}. Validate the inferred need; segment: {segment}."}

def analyse_request(title: str, description: str, segment: str) -> dict[str, Any]:
    key = os.getenv("OPENAI_API_KEY")
    if key and OpenAI:
        try:
            client = OpenAI(api_key=key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0.1,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Extract the customer's underlying problem, not just requested solution. Return JSON keys underlying_need, theme, impact, urgency, confidence, rationale. impact and urgency must be Low, Medium, or High. confidence 0-1. Do not invent facts."},
                    {"role": "user", "content": json.dumps({"title": title, "description": description, "customer_segment": segment})}
                ])
            data = json.loads(response.choices[0].message.content)
            data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", .5))))
            for field in ("underlying_need", "theme", "impact", "urgency", "rationale"):
                data[field] = str(data.get(field) or "Not established")
            if data["impact"] not in ["Low", "Medium", "High"]: data["impact"] = "Medium"
            if data["urgency"] not in ["Low", "Medium", "High"]: data["urgency"] = "Medium"
            return data
        except Exception:
            pass
    return _fallback_analysis(title, description, segment)

def find_similar(title: str, description: str, candidates: list[dict], threshold: float = .12) -> list[dict]:
    if not candidates: return []
    docs = [f"{title}. {description}"] + [f"{c['title']}. {c['description']}" for c in candidates]
    scores = None
    key = os.getenv("OPENAI_API_KEY")
    if key and OpenAI:
        try:
            response = OpenAI(api_key=key).embeddings.create(model="text-embedding-3-small", input=docs)
            scores = cosine_similarity([response.data[0].embedding], [x.embedding for x in response.data[1:]]).flatten()
        except Exception: pass
    if scores is None:
        try:
            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2)).fit_transform(docs)
            scores = cosine_similarity(matrix[:1], matrix[1:]).flatten()
        except ValueError: return []
    matches = [{"request_id": c["id"], "title": c["title"], "similarity": round(float(s), 3),
                "explanation": "Shared terms suggest overlapping customer intent; review context before merging."}
               for c, s in zip(candidates, scores) if float(s) >= threshold]
    return sorted(matches, key=lambda x: x["similarity"], reverse=True)[:5]

def priority_score(votes: int, impact: str, urgency: str, effort: int = 3, strategic_fit: int = 3) -> float:
    demand = min(votes / 20, 1) * 100
    levels = {"Low": 25, "Medium": 60, "High": 100}
    return round(demand*.35 + levels.get(impact, 60)*.25 + levels.get(urgency, 60)*.20
                 + max(1, min(5, strategic_fit))*20*.15 + (6-max(1, min(5, effort)))*20*.05, 1)

def generate_decision_brief(requests: list[dict]) -> dict[str, str]:
    if not requests:
        return {"summary": "No analysed requests are available.", "recommendation": "Analyse requests first."}
    top = requests[0]
    return {"summary": f"{len(requests)} analysed requests are in scope. The strongest opportunity is '{top['title']}' in {top.get('theme')}, supported by {top.get('vote_count', 0)} votes.",
            "recommendation": f"Investigate '{top['title']}' first (score {top.get('priority_score')}/100). Validate customer need, strategic fit and delivery effort before committing roadmap capacity."}
