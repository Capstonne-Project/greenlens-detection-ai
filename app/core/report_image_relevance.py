"""Heuristic: is this photo plausibly a pollution report vs irrelevant / ambiguous."""


def classify_image_relevance(
    *,
    mapped_pollution_boxes: int,
    raw_detector_boxes: int,
    max_mapped_confidence: float,
    relevance_min_confidence: float,
) -> str:
    """
    POLLUTION_LIKELY — có ít nhất một vùng nhận được là ô nhiễm (đã map BR) và conf đủ mạnh.
    NOT_POLLUTION_OR_UNRELATED — không có bbox map được hoặc model không báo có object.
    UNCLEAR_NEED_MANUAL_REVIEW — có object nhưng không map ô nhiễm / conf thấp: cần người xem.
    """
    if mapped_pollution_boxes <= 0:
        if raw_detector_boxes > 0:
            return "UNCLEAR_NEED_MANUAL_REVIEW"
        return "NOT_POLLUTION_OR_UNRELATED"

    if max_mapped_confidence < relevance_min_confidence:
        return "UNCLEAR_NEED_MANUAL_REVIEW"
    return "POLLUTION_LIKELY"
