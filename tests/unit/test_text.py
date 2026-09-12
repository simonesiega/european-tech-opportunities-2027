from opportunities.utils.text import contains_normalized_phrase


def test_normalized_phrase_matching_requires_word_boundaries() -> None:
    assert contains_normalized_phrase("software engineering intern 2027", "engineering intern")
    assert not contains_normalized_phrase("international software engineer", "intern")
    assert not contains_normalized_phrase("software internship", "")
