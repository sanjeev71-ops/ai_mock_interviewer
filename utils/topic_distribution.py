def build_topic_distribution(
    topics: list[str],
    number_of_questions: int,
) -> list[str]:
    if not topics:
        raise ValueError(
            "No topics available."
        )

    selected_topics = []

    for index in range(number_of_questions):
        topic = topics[
            index % len(topics)
        ]

        selected_topics.append(topic)

    return selected_topics
