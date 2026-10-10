from models.report import FinalReport
from services.groq_service import GroqService

from utils.scoring import (
    calculate_interview_score,
    calculate_technical_score,
    calculate_communication_score,
)


class ReportGenerator:
    def __init__(self, groq=None):
        self.groq = groq or GroqService()

    def generate(self, session):
        # Latest attempt per question wins. Older attempts are
        # kept in session.results as history but never scored.
        latest_by_id = {}

        for result in session.results:
            latest_by_id[
                result.question.question_id
            ] = result

        latest = [
            latest_by_id[question.question_id]
            for question in session.questions
            if question.question_id in latest_by_id
        ]

        evaluations = [
            result.evaluation
            for result in latest
        ]

        overall_score = calculate_interview_score(
            evaluations
        )

        technical_score = calculate_technical_score(
            evaluations
        )

        communication_score = calculate_communication_score(
            evaluations
        )

        question_results = []

        for result in latest:
            question_results.append({
                "question_id": result.question.question_id,
                "topic": result.question.topic,
                "score": result.evaluation.overall_score,
            })

        topic_scores = {}

        for result in latest:
            topic = result.question.topic
            score = result.evaluation.overall_score

            if topic not in topic_scores:
                topic_scores[topic] = []

            topic_scores[topic].append(score)

        topic_performance = {
            topic: round(
                sum(scores) / len(scores),
                2
            )
            for topic, scores in topic_scores.items()
        }

        evaluation_data = []

        for result in latest:
            question = result.question
            correct_option = question.options[
                question.correct_index
            ]

            evaluation_data.append({
                "question_id": question.question_id,
                "question": question.question,
                "topic": question.topic,
                "format": "multiple_choice",
                "options": question.options,
                "correct_option": correct_option,
                "candidate_answer": result.candidate_answer,
                "was_correct": (
                    result.evaluation.overall_score >= 10
                ),
                "explanation": question.explanation,
                "scores": {
                    "correctness":
                        result.evaluation.scores.correctness,

                    "technical_depth":
                        result.evaluation.scores.technical_depth,

                    "clarity":
                        result.evaluation.scores.clarity,

                    "completeness":
                        result.evaluation.scores.completeness,
                },

                "feedback": result.evaluation.feedback,

                "strengths": result.evaluation.strengths,

                "weaknesses": result.evaluation.weaknesses,
            })

        system_prompt = """
You are a senior technical interview assessor.

Generate a final interview performance report.

Return ONLY valid JSON.

Do not include markdown.
Do not invent information.
Base your conclusions only on the provided interview data.
"""

        user_prompt = f"""
Candidate interview configuration:

Role:
{session.role}

Experience level:
{session.experience_level}

Difficulty:
{session.difficulty}

Interview results:

{evaluation_data}

The Python application has already calculated:

Overall score:
{overall_score}

Technical score:
{technical_score}

Communication score:
{communication_score}

Topic performance:
{topic_performance}

Generate:

1. strengths
2. weaknesses
3. personalized recommendations

Rules:

- Strengths must be supported by the interview results.
- Weaknesses must be supported by the interview results.
- Recommendations should directly address weaknesses.
- Do not invent skills that were never evaluated.
- Do not change the calculated scores.
- Scores are 10 for a correct option, 0 otherwise.
- Keep recommendations practical.

Return:

{{
    "overall_score": {overall_score},
    "technical_score": {technical_score},
    "communication_score": {communication_score},

    "strengths": [],

    "weaknesses": [],

    "recommendations": [],

    "topic_performance": {{}},

    "question_results": []
}}
"""

        data = self.groq.generate_json(
            system_prompt,
            user_prompt,
        )

        # Override calculated fields with Python values.
        data["overall_score"] = overall_score
        data["technical_score"] = technical_score
        data["communication_score"] = communication_score

        data["topic_performance"] = topic_performance

        data["question_results"] = question_results

        return FinalReport.model_validate(data)
