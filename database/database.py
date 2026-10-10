import json
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(
        self,
        database_path: str | None = None,
    ):
        if database_path is None:
            # Project root = parent of the `database` package,
            # so the DB resolves correctly regardless of cwd.
            database_path = (
                Path(__file__).resolve().parent.parent
                / "data"
                / "interviews.db"
            )

        self.database_path = Path(
            database_path
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.initialize()

    # ------------------------------------------
    # Connection
    # ------------------------------------------

    def connect(self):
        connection = sqlite3.connect(
            self.database_path
        )

        connection.row_factory = sqlite3.Row

        return connection

    # ------------------------------------------
    # Initialize database
    # ------------------------------------------

    def initialize(self):
        connection = self.connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS interviews (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id TEXT UNIQUE NOT NULL,

                role TEXT NOT NULL,

                experience_level TEXT NOT NULL,

                difficulty TEXT NOT NULL,

                number_of_questions INTEGER NOT NULL,

                model TEXT,

                time_limit_minutes INTEGER,

                overall_score REAL,

                technical_score REAL,

                communication_score REAL,

                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id TEXT NOT NULL,

                question_id INTEGER NOT NULL,

                question TEXT NOT NULL,

                topic TEXT NOT NULL,

                difficulty TEXT NOT NULL,

                expected_concepts TEXT NOT NULL,

                options TEXT NOT NULL DEFAULT '[]',

                correct_index INTEGER NOT NULL DEFAULT 0,

                explanation TEXT NOT NULL DEFAULT '',

                FOREIGN KEY(session_id)
                    REFERENCES interviews(session_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS question_results (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id TEXT NOT NULL,

                question_id INTEGER NOT NULL,

                attempt INTEGER NOT NULL DEFAULT 1,

                candidate_answer TEXT NOT NULL,

                correctness REAL NOT NULL,

                technical_depth REAL NOT NULL,

                clarity REAL NOT NULL,

                completeness REAL NOT NULL,

                overall_score REAL NOT NULL,

                feedback TEXT NOT NULL,

                strengths TEXT NOT NULL,

                weaknesses TEXT NOT NULL,

                FOREIGN KEY(session_id)
                    REFERENCES interviews(session_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                session_id TEXT UNIQUE NOT NULL,

                strengths TEXT NOT NULL,

                weaknesses TEXT NOT NULL,

                recommendations TEXT NOT NULL,

                topic_performance TEXT NOT NULL,

                created_at TEXT NOT NULL,

                FOREIGN KEY(session_id)
                    REFERENCES interviews(session_id)
            )
            """
        )

        connection.commit()

        self._migrate(connection)

        connection.close()

    def _migrate(self, connection) -> None:
        """Additive migrations for pre-existing databases."""
        cursor = connection.cursor()

        cursor.execute("PRAGMA table_info(interviews)")
        columns = {row[1] for row in cursor.fetchall()}

        if "model" not in columns:
            cursor.execute(
                "ALTER TABLE interviews "
                "ADD COLUMN model TEXT"
            )

        if "time_limit_minutes" not in columns:
            cursor.execute(
                "ALTER TABLE interviews "
                "ADD COLUMN time_limit_minutes INTEGER"
            )

        cursor.execute("PRAGMA table_info(questions)")
        question_columns = {
            row[1] for row in cursor.fetchall()
        }

        if "options" not in question_columns:
            cursor.execute(
                "ALTER TABLE questions "
                "ADD COLUMN options TEXT NOT NULL DEFAULT '[]'"
            )

        if "correct_index" not in question_columns:
            cursor.execute(
                "ALTER TABLE questions "
                "ADD COLUMN correct_index INTEGER NOT NULL DEFAULT 0"
            )

        if "explanation" not in question_columns:
            cursor.execute(
                "ALTER TABLE questions "
                "ADD COLUMN explanation TEXT NOT NULL DEFAULT ''"
            )

        connection.commit()

    # ------------------------------------------
    # Save interview
    # ------------------------------------------

    def save_interview(
        self,
        session,
        report,
    ):
        connection = self.connect()

        cursor = connection.cursor()

        created_at = datetime.now().isoformat()

        # --------------------------------------
        # Interview
        # --------------------------------------

        cursor.execute(
            """
            INSERT OR REPLACE INTO interviews (

                session_id,
                role,
                experience_level,
                difficulty,
                number_of_questions,
                model,
                time_limit_minutes,
                overall_score,
                technical_score,
                communication_score,
                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,

            (
                session.session_id,
                session.role,
                session.experience_level,
                session.difficulty,
                session.number_of_questions,
                getattr(session, "model", "") or "",
                getattr(session, "time_limit_minutes", None),
                report.overall_score,
                report.technical_score,
                report.communication_score,
                created_at,
            ),
        )

        # --------------------------------------
        # Questions
        # --------------------------------------

        cursor.execute(
            """
            DELETE FROM questions
            WHERE session_id = ?
            """,
            (session.session_id,),
        )

        for question in session.questions:
            cursor.execute(
                """
                INSERT INTO questions (

                    session_id,
                    question_id,
                    question,
                    topic,
                    difficulty,
                    expected_concepts,
                    options,
                    correct_index,
                    explanation

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (
                    session.session_id,
                    question.question_id,
                    question.question,
                    question.topic,
                    question.difficulty,
                    json.dumps(
                        question.expected_concepts
                    ),
                    json.dumps(question.options),
                    question.correct_index,
                    question.explanation,
                ),
            )

        # --------------------------------------
        # Results (full attempt history)
        # --------------------------------------

        cursor.execute(
            """
            DELETE FROM question_results
            WHERE session_id = ?
            """,
            (session.session_id,),
        )

        for result in session.results:
            evaluation = result.evaluation

            cursor.execute(
                """
                INSERT INTO question_results (

                    session_id,
                    question_id,
                    attempt,
                    candidate_answer,
                    correctness,
                    technical_depth,
                    clarity,
                    completeness,
                    overall_score,
                    feedback,
                    strengths,
                    weaknesses

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (
                    session.session_id,

                    result.question.question_id,

                    result.attempt,

                    result.candidate_answer,

                    evaluation.scores.correctness,

                    evaluation.scores.technical_depth,

                    evaluation.scores.clarity,

                    evaluation.scores.completeness,

                    evaluation.overall_score,

                    evaluation.feedback,

                    json.dumps(
                        evaluation.strengths
                    ),

                    json.dumps(
                        evaluation.weaknesses
                    ),
                ),
            )

        # --------------------------------------
        # Report
        # --------------------------------------

        cursor.execute(
            """
            INSERT OR REPLACE INTO reports (

                session_id,
                strengths,
                weaknesses,
                recommendations,
                topic_performance,
                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?)
            """,

            (
                session.session_id,

                json.dumps(
                    report.strengths
                ),

                json.dumps(
                    report.weaknesses
                ),

                json.dumps(
                    report.recommendations
                ),

                json.dumps(
                    report.topic_performance
                ),

                created_at,
            ),
        )

        connection.commit()

        connection.close()

    # ------------------------------------------
    # Get interview history
    # ------------------------------------------

    def get_interviews(self):
        connection = self.connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *

            FROM interviews

            ORDER BY created_at DESC
            """
        )

        rows = cursor.fetchall()

        connection.close()

        return [dict(row) for row in rows]

    # ------------------------------------------
    # Get single interview
    # ------------------------------------------

    def get_interview(
        self,
        session_id: str,
    ):
        connection = self.connect()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT *

            FROM interviews

            WHERE session_id = ?
            """,
            (session_id,),
        )

        interview = cursor.fetchone()

        if interview is None:
            connection.close()

            return None

        # --------------------------------------
        # Questions
        # --------------------------------------

        cursor.execute(
            """
            SELECT *

            FROM questions

            WHERE session_id = ?

            ORDER BY question_id
            """,
            (session_id,),
        )

        questions = cursor.fetchall()

        # --------------------------------------
        # Results (insertion order = attempt order)
        # --------------------------------------

        cursor.execute(
            """
            SELECT *

            FROM question_results

            WHERE session_id = ?

            ORDER BY question_id, id
            """,
            (session_id,),
        )

        results = cursor.fetchall()

        # --------------------------------------
        # Report
        # --------------------------------------

        cursor.execute(
            """
            SELECT *

            FROM reports

            WHERE session_id = ?
            """,
            (session_id,),
        )

        report = cursor.fetchone()

        connection.close()

        return {
            "interview": dict(interview),
            "questions": [
                dict(row)
                for row in questions
            ],
            "results": [
                dict(row)
                for row in results
            ],
            "report": (
                dict(report)
                if report
                else None
            ),
        }
