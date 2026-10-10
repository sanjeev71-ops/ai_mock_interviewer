from pydantic import BaseModel, Field

from models.question import Question
from models.evaluation import Evaluation


class QuestionResult(BaseModel):
    question: Question
    candidate_answer: str
    evaluation: Evaluation
    attempt: int = 1


class InterviewSession(BaseModel):
    session_id: str

    role: str
    experience_level: str
    difficulty: str

    number_of_questions: int

    # Model serving this interview (pinned on first success).
    model: str = ""

    questions: list[Question] = Field(
        default_factory=list
    )

    results: list[QuestionResult] = Field(
        default_factory=list
    )

    current_question_index: int = 0

    # Interview state
    status: str = "created"

    # Result waiting to be displayed
    pending_result: QuestionResult | None = None

    # Free-navigation flags (question_ids)
    marked_for_review: list[int] = Field(
        default_factory=list
    )
    skipped: list[int] = Field(
        default_factory=list
    )

    # Whole-test timer (None = no limit)
    time_limit_minutes: int | None = None
    started_at: str = ""
