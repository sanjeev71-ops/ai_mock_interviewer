from pydantic import BaseModel, Field


class EvaluationScores(BaseModel):
    correctness: float = Field(ge=0, le=10)
    technical_depth: float = Field(ge=0, le=10)
    clarity: float = Field(ge=0, le=10)
    completeness: float = Field(ge=0, le=10)


class Evaluation(BaseModel):
    scores: EvaluationScores
    strengths: list[str]
    weaknesses: list[str]
    feedback: str

    @property
    def overall_score(self) -> float:
        scores = self.scores
        return round(
            (
                scores.correctness
                + scores.technical_depth
                + scores.clarity
                + scores.completeness
            )
            / 4,
            2,
        )
