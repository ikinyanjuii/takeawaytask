import os
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base, engine, get_db
from . import models, schemas
from .ai import analyse_request, find_similar, priority_score, generate_decision_brief

Base.metadata.create_all(bind=engine)
app = FastAPI(title="FeatureIQ API", version="1.0.0", description="AI-first feature intelligence and prioritisation")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "featureiq-api"}

def _out(req, db):
    analysis = db.query(models.AIAnalysis).filter_by(request_id=req.id).order_by(models.AIAnalysis.id.desc()).first()
    merged_ids = [r[0] for r in db.query(models.FeatureRequest.id).filter_by(merged_into_id=req.id).all()]
    votes = db.query(func.count(models.Vote.id)).filter(models.Vote.request_id.in_([req.id] + merged_ids)).scalar() or 0
    score = priority_score(votes, analysis.impact, analysis.urgency) if analysis else None
    return {"id": req.id, "title": req.title, "description": req.description, "customer_segment": req.customer_segment,
            "status": req.status, "created_at": req.created_at, "vote_count": votes,
            "theme": analysis.theme if analysis else None, "underlying_need": analysis.underlying_need if analysis else None,
            "priority_score": score}

@app.post("/api/requests", response_model=schemas.RequestOut, status_code=201)
def create_request(payload: schemas.RequestCreate, db: Session = Depends(get_db)):
    req = models.FeatureRequest(**payload.model_dump())
    db.add(req); db.commit(); db.refresh(req)
    return _out(req, db)

@app.get("/api/requests")
def list_requests(q: str = Query(default="", max_length=120), sort: str = "popular", db: Session = Depends(get_db)):
    query = db.query(models.FeatureRequest).filter(models.FeatureRequest.status != "Merged")
    if q:
        query = query.filter((models.FeatureRequest.title.ilike(f"%{q}%")) | (models.FeatureRequest.description.ilike(f"%{q}%")))
    results = [_out(r, db) for r in query.all()]
    if sort == "priority": results.sort(key=lambda x: x["priority_score"] or 0, reverse=True)
    elif sort == "newest": results.sort(key=lambda x: x["created_at"], reverse=True)
    else: results.sort(key=lambda x: x["vote_count"], reverse=True)
    return results

@app.get("/api/requests/{request_id}")
def get_request(request_id: int, db: Session = Depends(get_db)):
    req = db.get(models.FeatureRequest, request_id)
    if not req: raise HTTPException(404, "Request not found")
    return _out(req, db)

@app.post("/api/requests/{request_id}/vote")
def vote(request_id: int, payload: schemas.VoteIn, db: Session = Depends(get_db)):
    req = db.get(models.FeatureRequest, request_id)
    if not req: raise HTTPException(404, "Request not found")
    if req.status == "Merged": raise HTTPException(409, "Request has been merged")
    if db.query(models.Vote).filter_by(request_id=request_id, voter_key=payload.voter_key).first():
        raise HTTPException(409, "This voter has already supported this request")
    db.add(models.Vote(request_id=request_id, voter_key=payload.voter_key)); db.commit()
    return {"message": "Support recorded", "vote_count": db.query(models.Vote).filter_by(request_id=request_id).count()}

@app.post("/api/requests/{request_id}/analyse", response_model=schemas.AnalyseOut)
def analyse(request_id: int, db: Session = Depends(get_db)):
    req = db.get(models.FeatureRequest, request_id)
    if not req: raise HTTPException(404, "Request not found")
    result = analyse_request(req.title, req.description, req.customer_segment)
    db.add(models.AIAnalysis(request_id=request_id, **result)); db.commit()
    others = db.query(models.FeatureRequest).filter(models.FeatureRequest.id != request_id, models.FeatureRequest.status != "Merged").all()
    similar = find_similar(req.title, req.description, [{"id": r.id, "title": r.title, "description": r.description} for r in others])
    for match in similar:
        exists = db.query(models.MergeSuggestion).filter_by(source_request_id=request_id, target_request_id=match["request_id"], status="Pending").first()
        if not exists:
            db.add(models.MergeSuggestion(source_request_id=request_id, target_request_id=match["request_id"], similarity=match["similarity"], explanation=match["explanation"]))
    db.commit()
    return {"request_id": request_id, **result, "similar_requests": similar}

@app.get("/api/merge-suggestions")
def merge_suggestions(db: Session = Depends(get_db)):
    rows = db.query(models.MergeSuggestion).filter_by(status="Pending").order_by(models.MergeSuggestion.similarity.desc()).all()
    return [{"id": x.id, "source": {"id": db.get(models.FeatureRequest, x.source_request_id).id, "title": db.get(models.FeatureRequest, x.source_request_id).title},
             "target": {"id": db.get(models.FeatureRequest, x.target_request_id).id, "title": db.get(models.FeatureRequest, x.target_request_id).title},
             "similarity": x.similarity, "explanation": x.explanation} for x in rows]

@app.post("/api/merge-suggestions/{suggestion_id}/decision")
def decide_merge(suggestion_id: int, payload: schemas.MergeDecision, db: Session = Depends(get_db)):
    suggestion = db.get(models.MergeSuggestion, suggestion_id)
    if not suggestion: raise HTTPException(404, "Suggestion not found")
    if suggestion.status != "Pending": raise HTTPException(409, "Suggestion already reviewed")
    suggestion.status = "Approved" if payload.decision == "approve" else "Rejected"
    if payload.decision == "approve":
        source, target = db.get(models.FeatureRequest, suggestion.source_request_id), db.get(models.FeatureRequest, suggestion.target_request_id)
        if not source or not target: raise HTTPException(404, "Source or target no longer exists")
        if source.status == "Merged" or target.status == "Merged" or source.id == target.id:
            raise HTTPException(409, "Invalid merge state")
        source.status, source.merged_into_id = "Merged", target.id
        db.query(models.MergeSuggestion).filter(models.MergeSuggestion.source_request_id == source.id,
            models.MergeSuggestion.id != suggestion.id, models.MergeSuggestion.status == "Pending").update({"status": "Superseded"})
    db.commit()
    return {"status": suggestion.status, "message": "Human review decision saved"}

@app.get("/api/insights")
def insights(db: Session = Depends(get_db)):
    requests = db.query(models.FeatureRequest).all()
    analyses = db.query(models.AIAnalysis).all()
    active = {r.id for r in requests if r.status != "Merged"}
    themes = {}
    for a in analyses:
        if a.request_id in active: themes[a.theme] = themes.get(a.theme, 0) + 1
    return {"total_requests": len(active), "total_votes": db.query(models.Vote).count(),
            "analysed_requests": len({a.request_id for a in analyses if a.request_id in active}),
            "pending_merges": db.query(models.MergeSuggestion).filter_by(status="Pending").count(),
            "themes": [{"name": k, "count": v} for k, v in sorted(themes.items(), key=lambda x: x[1], reverse=True)]}

@app.post("/api/decision-briefs")
def create_brief(db: Session = Depends(get_db)):
    rows = [_out(r, db) for r in db.query(models.FeatureRequest).filter(models.FeatureRequest.status != "Merged").all()]
    rows = [r for r in rows if r["theme"]]
    if not rows: raise HTTPException(400, "Analyse at least one request first")
    rows.sort(key=lambda x: x["priority_score"] or 0, reverse=True)
    generated = generate_decision_brief(rows); top = rows[0]
    evidence = "\\n".join([f"- Request #{r['id']} — {r['title']}: score {r['priority_score']}/100; {r['vote_count']} votes; theme {r['theme']}." for r in rows[:5]])
    brief = models.DecisionBrief(title="Feature prioritisation decision brief", summary=generated["summary"],
        recommendation=generated["recommendation"], evidence=evidence, score=top["priority_score"])
    db.add(brief); db.commit(); db.refresh(brief)
    return {"id": brief.id, "title": brief.title, "summary": brief.summary, "recommendation": brief.recommendation, "evidence": brief.evidence, "score": brief.score}

@app.get("/api/decision-briefs")
def list_briefs(db: Session = Depends(get_db)):
    return [{"id": b.id, "title": b.title, "summary": b.summary, "recommendation": b.recommendation, "evidence": b.evidence, "score": b.score}
            for b in db.query(models.DecisionBrief).order_by(models.DecisionBrief.id.desc()).all()]

@app.post("/api/demo/seed")
def seed_demo(db: Session = Depends(get_db)):
    if db.query(models.FeatureRequest).count(): return {"message": "Database already contains requests"}
    examples = [
        ("Send alerts when a task is assigned", "I miss work because I only see assignments when I open the app. I need timely alerts.", "SMB teams"),
        ("Teams notifications for task updates", "Send a message whenever a task changes or a colleague assigns work.", "Enterprise"),
        ("Email reminders for important changes", "Our team misses updates and deadlines. Email us when tasks are assigned.", "Mid-market"),
        ("Export analytics to CSV", "Download filtered reports to CSV for monthly operational reviews.", "Operations"),
        ("Improve dashboard loading speed", "The dashboard takes too long to load during peak periods.", "Enterprise")]
    created = []
    for title, description, segment in examples:
        req = models.FeatureRequest(title=title, description=description, customer_segment=segment)
        db.add(req); db.flush(); created.append(req)
    for req, count in zip(created, [8, 12, 5, 4, 9]):
        for i in range(count): db.add(models.Vote(request_id=req.id, voter_key=f"demo-{req.id}-{i}"))
    db.commit()
    return {"message": "Demo requests created. Run AI analysis to generate insights and duplicate suggestions."}
