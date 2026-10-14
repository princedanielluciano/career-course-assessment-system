import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/exit-surveys", tags=["Curriculum Exit Survey"])

DB_PATH = Path(__file__).resolve().parent / "career_course.db"

EXIT_OPTIONS = {
    "College / Higher Education",
    "Employment",
    "Entrepreneurship",
    "TESDA / Middle Skills Development",
    "Other",
}


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def to_json_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


class ExitSurveyCreate(BaseModel):
    learner_reference_number: str = ""
    school_name: str = ""
    last_name: str = ""
    first_name: str
    middle_name: str = ""
    track: str = ""
    grade_section: str = ""
    age: Optional[int] = Field(default=None, ge=10, le=100)
    date_of_birth: str = ""
    home_address: str = ""
    father_name: str = ""
    father_occupation: str = ""
    mother_name: str = ""
    mother_occupation: str = ""
    parents_present_status: str = ""
    strand: str = ""
    sex: str = ""
    religion: str = ""
    place_of_birth: str = ""
    class_adviser: str = ""
    guidance_counselor: str = ""
    guidance_advocate: str = ""
    career_advocate: str = ""

    learnings: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)

    planned_exit: str
    reason_for_exit: str = ""

    college_choices: list[str] = Field(default_factory=list)
    study_support: list[str] = Field(default_factory=list)
    work_choices: list[str] = Field(default_factory=list)
    business_choices: list[str] = Field(default_factory=list)
    tesda_choices: list[str] = Field(default_factory=list)

    other_plans: list[str] = Field(default_factory=list)
    other_plans_reasons: str = ""

    recommend_school: str = ""
    recommendation_reason: str = ""
    student_signature: str = ""


def row_to_dict(row):
    item = dict(row)

    json_fields = [
        "learnings",
        "problems",
        "college_choices",
        "study_support",
        "work_choices",
        "business_choices",
        "tesda_choices",
        "other_plans",
    ]

    for field in json_fields:
        try:
            item[field] = json.loads(item.get(field) or "[]")
        except (json.JSONDecodeError, TypeError):
            item[field] = []

    return item


@router.post("", status_code=201)
def create_exit_survey(survey: ExitSurveyCreate):
    data = survey.model_dump()

    if not data["first_name"].strip():
        raise HTTPException(
            status_code=422,
            detail="First name is required."
        )

    if data["planned_exit"] not in EXIT_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail="Please choose a valid curriculum exit."
        )

    if data["recommend_school"] not in ("", "Yes", "No"):
        raise HTTPException(
            status_code=422,
            detail="recommend_school must be Yes, No, or blank."
        )

    json_fields = [
        "learnings",
        "problems",
        "college_choices",
        "study_support",
        "work_choices",
        "business_choices",
        "tesda_choices",
        "other_plans",
    ]

    for field in json_fields:
        data[field] = json.dumps(data[field], ensure_ascii=False)

    columns = list(data.keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)
    values = [data[column] for column in columns]

    connection = get_db()

    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            INSERT INTO exit_surveys ({column_names})
            VALUES ({placeholders})
            """,
            values,
        )
        connection.commit()

        new_id = cursor.lastrowid

        return {
            "message": "Curriculum Exit Survey saved successfully.",
            "id": new_id,
        }

    except sqlite3.Error as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {error}"
        )

    finally:
        connection.close()


@router.get("")
def get_exit_surveys(
    search: str = Query(default=""),
    planned_exit: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
):
    connection = get_db()

    try:
        sql = "SELECT * FROM exit_surveys WHERE 1=1"
        parameters = []

        if search.strip():
            term = f"%{search.strip()}%"
            sql += """
                AND (
                    first_name LIKE ?
                    OR last_name LIKE ?
                    OR school_name LIKE ?
                    OR strand LIKE ?
                )
            """
            parameters.extend([term, term, term, term])

        if planned_exit.strip():
            sql += " AND planned_exit = ?"
            parameters.append(planned_exit.strip())

        sql += " ORDER BY id DESC LIMIT ?"
        parameters.append(limit)

        rows = connection.execute(sql, parameters).fetchall()

        return [row_to_dict(row) for row in rows]

    finally:
        connection.close()


@router.get("/analytics")
def exit_survey_analytics():
    connection = get_db()

    try:
        rows = connection.execute(
            "SELECT * FROM exit_surveys ORDER BY id DESC"
        ).fetchall()

        surveys = [row_to_dict(row) for row in rows]

        def count_values(field):
            counts = {}
            for survey in surveys:
                for value in survey.get(field, []):
                    value = str(value).strip()
                    if value:
                        counts[value] = counts.get(value, 0) + 1
            return [
                {"label": key, "count": value}
                for key, value in sorted(
                    counts.items(),
                    key=lambda item: (-item[1], item[0])
                )
            ]

        def count_field(field):
            counts = {}
            for survey in surveys:
                value = str(survey.get(field) or "").strip()
                if value:
                    counts[value] = counts.get(value, 0) + 1
            return [
                {"label": key, "count": value}
                for key, value in sorted(
                    counts.items(),
                    key=lambda item: (-item[1], item[0])
                )
            ]

        return {
            "total_responses": len(surveys),
            "curriculum_exits": count_field("planned_exit"),
            "strands": count_field("strand"),
            "tracks": count_field("track"),
            "learnings": count_values("learnings"),
            "problems": count_values("problems"),
            "study_support": count_values("study_support"),
            "college_choices": count_values("college_choices"),
            "work_choices": count_values("work_choices"),
            "business_choices": count_values("business_choices"),
            "tesda_choices": count_values("tesda_choices"),
            "other_plans": count_values("other_plans"),
            "school_recommendations": count_field("recommend_school"),
        }

    finally:
        connection.close()


@router.get("/{survey_id}")
def get_exit_survey(survey_id: int):
    connection = get_db()

    try:
        row = connection.execute(
            "SELECT * FROM exit_surveys WHERE id = ?",
            (survey_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Curriculum Exit Survey not found."
            )

        return row_to_dict(row)

    finally:
        connection.close()