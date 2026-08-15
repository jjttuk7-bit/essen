from app.services.signal.redundancy import find_redundant_segments


def test_normalized_duplicate_is_marked_with_a_preserved_reason() -> None:
    labels = find_redundant_segments([
        ("seg_1", "Ship the plan now."),
        ("seg_2", "ship   the plan now"),
    ])
    assert labels == [("seg_2", "동일 의미가 seg_1에 더 구체적으로 존재함")]
