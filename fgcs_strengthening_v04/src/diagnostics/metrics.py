"""Pair-level and checkpoint-level summaries for the registered noise floor."""

from itertools import combinations
import math

import numpy as np

from ..identity import RESOURCES
from .batches import PAIRS

_CROSS = tuple(combinations(RESOURCES, 2))


def pair_metrics(A, B):
    """Compute C, N and their difference with exact zero-norm exclusion."""
    arrays = {}
    for side, gradients in (("A", A), ("B", B)):
        if set(gradients) != set(RESOURCES):
            raise ValueError("Expected all four task gradients on both batches")
        arrays[side] = {task: np.asarray(gradients[task], dtype=np.float64) for task in RESOURCES}
    shapes = {vector.shape for tasks in arrays.values() for vector in tasks.values()}
    if (len(shapes) != 1 or any(vector.ndim != 1 or not len(vector) or not np.isfinite(vector).all()
                                for tasks in arrays.values() for vector in tasks.values())):
        raise ValueError("Expected finite nonempty gradient vectors of a common shape")
    norms = {side: {task: float(np.linalg.norm(vector)) for task, vector in tasks.items()}
             for side, tasks in arrays.items()}
    zeros = [{"side": side, "task": task} for side, tasks in norms.items()
             for task, norm in tasks.items() if norm == 0]

    def comparison(left, right_side, right):
        dot = float(np.dot(arrays["A"][left], arrays[right_side][right]))
        first, second = norms["A"][left], norms[right_side][right]
        return {"left_task": left, "right_task": right, "dot": dot,
                "cosine": dot / (first * second) if first and second else None,
                "norm_ratio_left_over_right": first / second if second else None}

    cross = [comparison(left, "A", right) for left, right in _CROSS]
    same = [comparison(task, "B", task) for task in RESOURCES]
    C = sum(item["dot"] < 0 for item in cross) / len(_CROSS) if not zeros else None
    N = sum(item["dot"] < 0 for item in same) / len(RESOURCES) if not zeros else None
    return {"C": C, "N": N, "K_pair": C - N if not zeros else None,
            "norms": norms, "zero_gradients": zeros, "cross_task": cross, "same_task": same}


def slot_metrics(pairs):
    if len(pairs) != PAIRS:
        raise ValueError("A diagnostic slot must contain exactly eight pairs")
    scores = [pair["K_pair"] for pair in pairs]

    def frequencies(key, count):
        output = []
        for i in range(count):
            rows = [pair[key][i] for pair in pairs]
            cosines = [row["cosine"] for row in rows if row["cosine"] is not None]
            negative = sum(value < 0 for value in cosines)
            output.append({"left_task": rows[0]["left_task"], "right_task": rows[0]["right_task"],
                           "negative": negative, "defined": len(cosines),
                           "frequency": negative / len(cosines) if cosines else None})
        return output

    cross = frequencies("cross_task", len(_CROSS))
    matrix = {task: {other: None for other in RESOURCES} for task in RESOURCES}
    for row in cross:
        left, right = row["left_task"], row["right_task"]
        matrix[left][right] = matrix[right][left] = row["frequency"]
    return {"K": math.fsum(scores) / PAIRS if all(value is not None for value in scores) else None,
            "complete_pairs": sum(value is not None for value in scores),
            "zero_gradient_count": sum(len(pair["zero_gradients"]) for pair in pairs),
            "cross_negative_cosine_frequency": cross,
            "same_negative_cosine_frequency": frequencies("same_task", len(RESOURCES)),
            "task_pair_negative_cosine_matrix": matrix}
