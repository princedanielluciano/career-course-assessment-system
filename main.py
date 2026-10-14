
from pathlib import Path
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import get_connection, init_db
from question_excel import router as question_excel_router
from program_matching import router as program_matching_router
from exit_survey import router as exit_survey_router


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"


# Create the FastAPI application first.
app = FastAPI(
    title="CareerPath API",
    description="Career and College Course Assessment and Decision-Support System",
    version="1.0.0"
)


# Initialize tables without deleting existing records.
init_db()


# Register additional API routers after creating the app.
app.include_router(question_excel_router)
app.include_router(program_matching_router)
app.include_router(exit_survey_router)


# Serve frontend files.
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static"
)


# -------------------------
# FRONTEND AND HEALTH CHECK
# -------------------------

@app.get("/", include_in_schema=False)
def home():
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Frontend file not found. Check frontend/index.html."
        )

    return FileResponse(index_file)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "CareerPath API is running."}


@app.get("/api/database/tables")
def database_tables():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

    return {"tables": [row["name"] for row in rows]}


# -------------------------
# REQUEST MODELS
# -------------------------

class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str | None = None
    grade_level: str = "Grade 12"
    strand: str | None = None


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    category: str = Field(min_length=1)
    option_a: str = Field(min_length=1)
    option_b: str = Field(min_length=1)
    option_c: str | None = None
    option_d: str | None = None
    is_active: bool = True


class ScoreRuleCreate(BaseModel):
    question_id: int
    option_code: str
    interest_category: str = Field(min_length=1)
    points: float = 1


class AnswerCreate(BaseModel):
    student_id: int
    question_id: int
    selected_option: str


class AssessmentCreate(BaseModel):
    student_id: int


class ProgramCreate(BaseModel):
    program_name: str = Field(min_length=1)
    description: str | None = None
    duration_years: int | None = Field(default=None, ge=1, le=10)
    skills_required: str | None = None
    career_opportunities: str | None = None


class SchoolCreate(BaseModel):
    school_name: str = Field(min_length=1)
    location: str | None = None
    website: str | None = None
    contact_details: str | None = None


# -------------------------
# STUDENTS
# -------------------------

@app.get("/api/students")
def get_students():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, full_name, email, grade_level, strand, created_at
            FROM students
            ORDER BY id DESC
        """).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/students", status_code=201)
def create_student(student: StudentCreate):
    full_name = student.full_name.strip()

    if not full_name:
        raise HTTPException(422, "Student name is required.")

    email = student.email.strip() if student.email else None
    email = email or None

    try:
        with get_connection() as connection:
            cursor = connection.execute("""
                INSERT INTO students
                    (full_name, email, grade_level, strand)
                VALUES (?, ?, ?, ?)
            """, (
                full_name,
                email,
                student.grade_level.strip() or "Grade 12",
                student.strand.strip() if student.strand else None
            ))

            row = connection.execute(
                "SELECT * FROM students WHERE id = ?",
                (cursor.lastrowid,)
            ).fetchone()

        return dict(row)

    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="That email may already be registered. Use a different email."
        ) from error


@app.get("/api/students/{student_id}")
def get_student(student_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Student not found.")

    return dict(row)


# -------------------------
# QUESTIONS
# -------------------------

@app.get("/api/questions")
def get_questions():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, question_text, category,
                   option_a, option_b, option_c, option_d,
                   is_active, created_at
            FROM questions
            WHERE is_active = 1
            ORDER BY id
        """).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/questions", status_code=201)
def create_question(question: QuestionCreate):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO questions (
                question_text, category,
                option_a, option_b, option_c, option_d, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            question.question_text.strip(),
            question.category.strip(),
            question.option_a.strip(),
            question.option_b.strip(),
            question.option_c.strip() if question.option_c else None,
            question.option_d.strip() if question.option_d else None,
            1 if question.is_active else 0
        ))

        row = connection.execute(
            "SELECT * FROM questions WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


@app.get("/api/questions/{question_id}")
def get_question(question_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM questions WHERE id = ?",
            (question_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Question not found.")

    return dict(row)


# -------------------------
# QUESTION SCORING RULES
# -------------------------

@app.post("/api/question-option-scores", status_code=201)
def create_score_rule(rule: ScoreRuleCreate):
    option_code = rule.option_code.upper().strip()

    if option_code not in {"A", "B", "C", "D"}:
        raise HTTPException(422, "Option code must be A, B, C, or D.")

    with get_connection() as connection:
        question = connection.execute(
            "SELECT id FROM questions WHERE id = ?",
            (rule.question_id,)
        ).fetchone()

        if question is None:
            raise HTTPException(404, "Question not found.")

        try:
            cursor = connection.execute("""
                INSERT INTO question_option_scores
                    (question_id, option_code, interest_category, points)
                VALUES (?, ?, ?, ?)
            """, (
                rule.question_id,
                option_code,
                rule.interest_category.strip(),
                rule.points
            ))
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail="A scoring rule already exists for this question and option."
            ) from error

        row = connection.execute(
            "SELECT * FROM question_option_scores WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


@app.get("/api/question-option-scores")
def get_score_rules():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM question_option_scores
            ORDER BY question_id, option_code
        """).fetchall()

    return [dict(row) for row in rows]


# -------------------------
# STUDENT ANSWERS
# -------------------------

@app.post("/api/answers", status_code=201)
def create_answer(answer: AnswerCreate):
    option_code = answer.selected_option.upper().strip()

    if option_code not in {"A", "B", "C", "D"}:
        raise HTTPException(422, "Selected option must be A, B, C, or D.")

    with get_connection() as connection:
        student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (answer.student_id,)
        ).fetchone()

        question = connection.execute(
            "SELECT * FROM questions WHERE id = ? AND is_active = 1",
            (answer.question_id,)
        ).fetchone()

        if student is None:
            raise HTTPException(404, "Student not found.")

        if question is None:
            raise HTTPException(404, "Active question not found.")

        option_field = f"option_{option_code.lower()}"

        if not question[option_field]:
            raise HTTPException(422, "That answer option is not available.")

        try:
            cursor = connection.execute("""
                INSERT INTO student_answers
                    (student_id, question_id, selected_option)
                VALUES (?, ?, ?)
            """, (
                answer.student_id,
                answer.question_id,
                option_code
            ))
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "This student already has an answer for this question. "
                    "For a new demo, use a new test student or a new question."
                )
            ) from error

        row = connection.execute(
            "SELECT * FROM student_answers WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


@app.get("/api/answers")
def get_answers(student_id: int | None = None):
    query = """
        SELECT sa.*, s.full_name, q.question_text
        FROM student_answers sa
        JOIN students s ON s.id = sa.student_id
        JOIN questions q ON q.id = sa.question_id
    """
    params = ()

    if student_id is not None:
        query += " WHERE sa.student_id = ?"
        params = (student_id,)

    query += " ORDER BY sa.id DESC"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]


# -------------------------
# COURSE PROGRAMS
# -------------------------

@app.get("/api/programs")
def get_programs():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, program_name, description, duration_years,
                   skills_required, career_opportunities
            FROM programs
            ORDER BY program_name
        """).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/programs", status_code=201)
def create_program(program: ProgramCreate):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO programs (
                program_name, description, duration_years,
                skills_required, career_opportunities
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            program.program_name.strip(),
            program.description,
            program.duration_years,
            program.skills_required,
            program.career_opportunities
        ))

        row = connection.execute(
            "SELECT * FROM programs WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


# -------------------------
# SCHOOLS
# -------------------------

@app.get("/api/schools")
def get_schools():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, school_name, location, website, contact_details
            FROM schools
            ORDER BY school_name
        """).fetchall()

    return [dict(row) for row in rows]


@app.post("/api/schools", status_code=201)
def create_school(school: SchoolCreate):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO schools
                (school_name, location, website, contact_details)
            VALUES (?, ?, ?, ?)
        """, (
            school.school_name.strip(),
            school.location,
            school.website,
            school.contact_details
        ))

        row = connection.execute(
            "SELECT * FROM schools WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return dict(row)


# -------------------------
# COURSE RECOMMENDATION
# -------------------------

def find_recommended_program(connection, category):
    category_lower = category.lower()

    keyword_groups = {
        "technology": [
            "information technology", "computer science",
            "computer engineering", "information systems",
            "software", "programming", "technology"
        ],
        "education": [
            "education", "teacher", "teaching"
        ],
        "business": [
            "business administration", "accountancy",
            "management", "entrepreneurship", "marketing",
            "financial management", "business"
        ],
        "arts": [
            "fine arts", "multimedia arts", "communication",
            "graphic design", "design"
        ],
        "health": [
            "nursing", "medical technology", "public health",
            "health sciences", "midwifery"
        ],
        "engineering": [
            "engineering", "civil engineering", "electrical engineering"
        ],
        "hospitality": [
            "hospitality management", "tourism management",
            "hotel", "restaurant"
        ]
    }

    keywords = keyword_groups.get(category_lower, [category_lower])

    programs = connection.execute("""
        SELECT * FROM programs ORDER BY program_name
    """).fetchall()

    for program in programs:
        searchable = " ".join([
            program["program_name"] or "",
            program["description"] or "",
            program["skills_required"] or "",
            program["career_opportunities"] or ""
        ]).lower()

        if any(keyword in searchable for keyword in keywords):
            return program

    return None


# -------------------------
# ASSESSMENTS AND RESULTS
# -------------------------

@app.post("/api/assessments", status_code=201)
def create_assessment(assessment: AssessmentCreate):
    with get_connection() as connection:
        student = connection.execute(
            "SELECT * FROM students WHERE id = ?",
            (assessment.student_id,)
        ).fetchone()

        if student is None:
            raise HTTPException(404, "Student not found.")

        answer_rows = connection.execute("""
            SELECT sa.question_id, sa.selected_option,
                   qos.interest_category, qos.points
            FROM student_answers sa
            JOIN question_option_scores qos
              ON qos.question_id = sa.question_id
             AND qos.option_code = sa.selected_option
            WHERE sa.student_id = ?
        """, (assessment.student_id,)).fetchall()

        if not answer_rows:
            raise HTTPException(
                400,
                "No scored answers found. Submit answers and add scoring rules first."
            )

        category_scores = {}

        for answer in answer_rows:
            category = answer["interest_category"]
            points = float(answer["points"])
            category_scores[category] = (
                category_scores.get(category, 0) + points
            )

        total_score = sum(category_scores.values())

        strongest_interest = sorted(
            category_scores.items(),
            key=lambda item: (-item[1], item[0].lower())
        )[0][0]

        strongest_score = category_scores[strongest_interest]
        matching_score = (
            round((strongest_score / total_score) * 100, 2)
            if total_score else 0
        )

        recommended_program = find_recommended_program(
            connection,
            strongest_interest
        )

        recommended_program_id = (
            recommended_program["id"] if recommended_program else None
        )

        recommended_course = (
            recommended_program["program_name"]
            if recommended_program else None
        )

        if recommended_course:
            recommendation_note = (
                "This program matched the strongest recorded interest. "
                "Discuss the result with guidance personnel before deciding."
            )
        else:
            recommendation_note = (
                "No matching course was found in the programs database. "
                "Add relevant college programs before generating a course recommendation."
            )

        summary = {
            "student_name": student["full_name"],
            "answered_questions": len(answer_rows),
            "category_scores": category_scores,
            "strongest_interest": strongest_interest,
            "recommended_course": recommended_course,
            "recommendation_note": recommendation_note
        }

        cursor = connection.execute("""
            INSERT INTO assessment_results (
                student_id, recommended_program_id, total_score,
                matching_score, result_summary
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            assessment.student_id,
            recommended_program_id,
            total_score,
            matching_score,
            json.dumps(summary)
        ))

        row = connection.execute(
            "SELECT * FROM assessment_results WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    result = dict(row)

    try:
        result["result_summary"] = json.loads(result["result_summary"])
    except (TypeError, json.JSONDecodeError):
        result["result_summary"] = {}

    return result


@app.get("/api/assessments")
def get_assessments():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM assessment_results
            ORDER BY id DESC
        """).fetchall()

    results = []

    for row in rows:
        result = dict(row)

        try:
            result["result_summary"] = json.loads(
                result["result_summary"] or "{}"
            )
        except (TypeError, json.JSONDecodeError):
            result["result_summary"] = {}

        results.append(result)

    return results


@app.get("/api/assessments/{assessment_id}")
def get_assessment(assessment_id: int):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM assessment_results WHERE id = ?",
            (assessment_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(404, "Assessment result not found.")

    result = dict(row)

    try:
        result["result_summary"] = json.loads(
            result["result_summary"] or "{}"
        )
    except (TypeError, json.JSONDecodeError):
        result["result_summary"] = {}

    return result