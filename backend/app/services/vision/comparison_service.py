from collections import Counter
from typing import Any


def _change_type(previous: int, current: int) -> str:
    if current > previous:
        return "INCREASE"
    if current < previous:
        return "DECREASE"
    return "UNCHANGED"


def compare_detections(previous: list[dict], current: list[dict]) -> dict[str, list[dict[str, Any]]]:
    previous_counts = Counter(item["class_name"] for item in previous)
    current_counts = Counter(item["class_name"] for item in current)
    classes = sorted(set(previous_counts) | set(current_counts))
    changed = []
    for class_name in classes:
        previous_count = previous_counts[class_name]
        current_count = current_counts[class_name]
        changed.append({
            "class_name": class_name,
            "previous_count": previous_count,
            "current_count": current_count,
            "change": current_count - previous_count,
            "change_type": _change_type(previous_count, current_count),
        })
    return {
        "added": [item for item in changed if item["change_type"] == "INCREASE"],
        "removed": [item for item in changed if item["change_type"] == "DECREASE"],
        "changed": [item for item in changed if item["change_type"] == "UNCHANGED"],
    }
