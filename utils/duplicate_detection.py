import re


STOP_WORDS = {
    "what",
    "is",
    "are",
    "the",
    "a",
    "an",
    "in",
    "of",
    "to",
    "and",
    "how",
    "why",
    "explain",
    "describe",
    "does",
    "do",
}


def normalize_text(text: str) -> set[str]:
    words = re.findall(
        r"\b[a-zA-Z0-9]+\b",
        text.lower(),
    )

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def similarity(
    text_a: str,
    text_b: str,
) -> float:
    words_a = normalize_text(text_a)

    words_b = normalize_text(text_b)

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b

    union = words_a | words_b

    return len(intersection) / len(union)


def has_duplicate_questions(
    questions,
    threshold: float = 0.65,
) -> bool:
    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            score = similarity(
                questions[i].question,
                questions[j].question,
            )

            if score >= threshold:
                return True

    return False
