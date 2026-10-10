from pydantic import BaseModel, Field


class QuestionResultSummary(BaseModel):
    question_id: int
    topic: str
    score: float


class FinalReport(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    technical_score: float = Field(ge=0, le=10)
    communication_score: float = Field(ge=0, le=10)

    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]

    topic_performance: dict[str, float]

    question_results: list[QuestionResultSummary]
