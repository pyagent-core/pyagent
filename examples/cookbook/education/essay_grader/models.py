"""Pydantic models for Essay Grader."""
from __future__ import annotations
from pydantic import BaseModel


class GradeRequest(BaseModel):
    essay_id: str
    essay: str


class GradeResponse(BaseModel):
    essay_id: str
    grade: str
    rationale: str
    grammar_grade: str
    cost_usd: float
    trace_file: str


def parse_grade(output: str) -> str:
    """Extract single letter A-F from the first line of grader output."""
    first_line = output.strip().splitlines()[0] if output.strip() else ""
    for char in first_line.upper():
        if char in "ABCDEF":
            return char
    return "F"
