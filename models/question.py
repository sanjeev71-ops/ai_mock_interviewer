from pydantic import BaseModel, Field


class Question(BaseModel):
    question_id: int
    question: str
    topic: str
    difficulty: str
    expected_concepts: list[str]
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str = ""


class QuestionSet(BaseModel):
    questions: list[Question]
