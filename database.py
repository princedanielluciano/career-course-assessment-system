import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "career_course.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                grade_level TEXT NOT NULL DEFAULT 'Grade 12',
                strand TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_name TEXT NOT NULL,
                location TEXT,
                website TEXT,
                contact_details TEXT
            );

            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_name TEXT NOT NULL,
                description TEXT,
                duration_years INTEGER,
                skills_required TEXT,
                career_opportunities TEXT
            );

            CREATE TABLE IF NOT EXISTS school_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                program_id INTEGER NOT NULL,
                estimated_tuition REAL DEFAULT 0,
                miscellaneous_fees REAL DEFAULT 0,
                academic_year TEXT,
                FOREIGN KEY (school_id) REFERENCES schools(id),
                FOREIGN KEY (program_id) REFERENCES programs(id),
                UNIQUE (school_id, program_id, academic_year)
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                category TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT,
                option_d TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS assessment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                recommended_program_id INTEGER,
                total_score REAL DEFAULT 0,
                matching_score REAL DEFAULT 0,
                result_summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (recommended_program_id)
                    REFERENCES programs(id)
            );

            
            
            CREATE TABLE IF NOT EXISTS student_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_option TEXT NOT NULL,
                answered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (question_id) REFERENCES questions(id),
                UNIQUE (student_id, question_id)
            );

            
            
CREATE TABLE IF NOT EXISTS question_option_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_code TEXT NOT NULL
        CHECK (option_code IN ('A', 'B', 'C', 'D')),
    interest_category TEXT NOT NULL,
    points REAL NOT NULL DEFAULT 1,
    FOREIGN KEY (question_id) REFERENCES questions(id),
    UNIQUE (question_id, option_code)
);

        """)


if __name__ == "__main__":
    init_db()
    print("Database created successfully!")
    print(f"Database location: {DATABASE_PATH}")
# ==========================================================
# CAREERPATH: CURRICULUM EXIT SURVEY TABLES
# Safe addition: hindi nito binubura ang existing records.
# ==========================================================

def init_exit_survey_db():
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).resolve().parent / "career_course.db"
    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exit_surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_reference_number TEXT,
                school_name TEXT,
                last_name TEXT,
                first_name TEXT,
                middle_name TEXT,
                track TEXT,
                grade_section TEXT,
                age INTEGER,
                date_of_birth TEXT,
                home_address TEXT,
                father_name TEXT,
                father_occupation TEXT,
                mother_name TEXT,
                mother_occupation TEXT,
                parents_present_status TEXT,
                strand TEXT,
                sex TEXT,
                religion TEXT,
                place_of_birth TEXT,
                class_adviser TEXT,
                guidance_counselor TEXT,
                guidance_advocate TEXT,
                career_advocate TEXT,
                learnings TEXT NOT NULL DEFAULT '[]',
                problems TEXT NOT NULL DEFAULT '[]',
                planned_exit TEXT NOT NULL,
                reason_for_exit TEXT,
                college_choices TEXT NOT NULL DEFAULT '[]',
                study_support TEXT NOT NULL DEFAULT '[]',
                work_choices TEXT NOT NULL DEFAULT '[]',
                business_choices TEXT NOT NULL DEFAULT '[]',
                tesda_choices TEXT NOT NULL DEFAULT '[]',
                other_plans TEXT NOT NULL DEFAULT '[]',
                other_plans_reasons TEXT,
                recommend_school TEXT,
                recommendation_reason TEXT,
                student_signature TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()
        print("CareerPath Curriculum Exit Survey tables are ready.")

    finally:
        connection.close()


# Run the safe initialization when this file is imported.
init_exit_survey_db()