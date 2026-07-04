"""Pydantic models for SQL Analyst."""
from __future__ import annotations
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query_id: str
    question: str


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    sql: str
    cost_usd: float
    trace_file: str
