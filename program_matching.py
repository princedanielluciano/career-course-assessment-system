import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(prefix="/api/program-matching", tags=["Program Matching"])
DB_PATH = Path(__file__).resolve().parent / "career_course.db"


@router.get("")
def match_programs(
    skills: str = Query(..., min_length=1, description="Comma-separated skills"),
):
    student_skills = [
        item.strip().lower()
        for item in skills.split(",")
        if item.strip()
    ]

    if not student_skills:
        raise HTTPException(status_code=400, detail="Enter at least one skill.")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        programs = connection.execute(
            """
            SELECT id, program_name, description, duration_years,
                   skills_required, career_opportunities
            FROM programs
            ORDER BY program_name
            """
        ).fetchall()

        results = []

        for program in programs:
            required_text = str(program["skills_required"] or "")
            required_skills = [
                item.strip().lower()
                for item in required_text.replace(";", ",").split(",")
                if item.strip()
            ]

            matched = [
                skill for skill in student_skills
                if any(
                    skill in required or required in skill
                    for required in required_skills
                )
            ]

            percentage = round(
                len(set(matched)) / len(set(student_skills)) * 100
            )

            results.append({
                "program_id": program["id"],
                "program_name": program["program_name"],
                "description": program["description"],
                "duration_years": program["duration_years"],
                "skills_required": required_text,
                "career_opportunities": program["career_opportunities"],
                "matched_skills": matched,
                "matching_score": percentage,
            })

        results.sort(
            key=lambda item: item["matching_score"],
            reverse=True,
        )

        return {
            "student_skills": student_skills,
            "results": results,
            "note": (
                "Rule-based matching prototype. Scores are based on text "
                "matching and are not a validated aptitude assessment."
            ),
        }

    finally:
        connection.close()