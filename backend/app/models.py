from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base

class FeatureRequest(Base):
    __tablename__ = "feature_requests"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False)
    customer_segment = Column(String(100), default="Unspecified")
    status = Column(String(30), default="Under review")
    merged_into_id = Column(Integer, ForeignKey("feature_requests.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    votes = relationship("Vote", back_populates="request", cascade="all, delete-orphan")
    analyses = relationship("AIAnalysis", back_populates="request", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("feature_requests.id"), nullable=False)
    voter_key = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    request = relationship("FeatureRequest", back_populates="votes")

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"
    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("feature_requests.id"), nullable=False)
    underlying_need = Column(Text, default="")
    theme = Column(String(160), default="Uncategorised")
    impact = Column(String(30), default="Medium")
    urgency = Column(String(30), default="Medium")
    confidence = Column(Float, default=0.5)
    rationale = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    request = relationship("FeatureRequest", back_populates="analyses")

class MergeSuggestion(Base):
    __tablename__ = "merge_suggestions"
    id = Column(Integer, primary_key=True)
    source_request_id = Column(Integer, ForeignKey("feature_requests.id"), nullable=False)
    target_request_id = Column(Integer, ForeignKey("feature_requests.id"), nullable=False)
    similarity = Column(Float, nullable=False)
    explanation = Column(Text, default="")
    status = Column(String(30), default="Pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DecisionBrief(Base):
    __tablename__ = "decision_briefs"
    id = Column(Integer, primary_key=True)
    title = Column(String(180), nullable=False)
    summary = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
