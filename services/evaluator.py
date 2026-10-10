from models.evaluation import Evaluation
from services.groq_service import GroqService


class AnswerEvaluator:
    def __init__(self, groq=None):
        self.groq = groq or GroqService()

    def evaluate(
        self,
        role: str,
        experience_level: str,
        difficulty: str,
        question: str,
        topic: str,
        expected_concepts: list[str],
        candidate_answer: str,
    ) -> Evaluation:
        system_prompt = """
You are a senior technical interviewer.

Evaluate the candidate's answer objectively.

Return ONLY valid JSON.

Do not include markdown.
Do not reveal the expected answer.
"""

        user_prompt = f"""
Evaluate this candidate answer.

Role:
{role}

Experience:
{experience_level}

Difficulty:
{difficulty}

Topic:
{topic}

Question:
{question}

Expected concepts:
{expected_concepts}

Candidate answer:
{candidate_answer}

Evaluation criteria:

Correctness:
0-10

Technical depth:
0-10

Clarity:
0-10

Completeness:
0-10

Rules:

1. Compare the answer against the expected concepts.
2. Do not give credit for concepts the candidate did not demonstrate.
3. Do not require exact wording.
4. Correct alternative explanations should receive credit.
5. Do not reveal the expected answer.
6. Explain the reasoning behind the scores.
7. Feedback must be constructive.
8. Identify specific strengths.
9. Identify specific weaknesses.

Return:

{{
    "scores": {{
        "correctness": 0,
        "technical_depth": 0,
        "clarity": 0,
        "completeness": 0
    }},
    "strengths": [],
    "weaknesses": [],
    "feedback": "..."
}}
"""

        data = self.groq.generate_json(
            system_prompt,
            user_prompt,
        )

        return Evaluation.model_validate(data)
