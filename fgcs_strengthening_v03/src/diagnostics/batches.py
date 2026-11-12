"""Stateless v0.3 batch draws from the ordered legal outer-training origin set."""

from dataclasses import dataclass
from hashlib import sha256
import operator

import numpy as np

from ..identity import ScientificIdentity, canonical_json, read_config

_SETTINGS = read_config()["diagnostics"]
BATCH_SIZE = _SETTINGS["batch_size"]
PAIRS = _SETTINGS["pairs"]


def json_sha256(value):
    return sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class Draw:
    key: str
    indices: tuple[int, ...]
    origin_ids: tuple[int | str, ...]

    def payload(self):
        ids = list(self.origin_ids)
        return {"key": self.key, "indices": list(self.indices), "origin_ids": ids,
                "origin_ids_sha256": json_sha256(ids)}


@dataclass(frozen=True, slots=True)
class BatchPair:
    index: int
    A: Draw
    B: Draw

    def payload(self):
        return {"pair_index": self.index, "A": self.A.payload(), "B": self.B.payload()}


def build_batch_pairs(identity, legal_outer_train_ids):
    """Draw from canonical window order. The engine supplies the verified train set."""
    if not isinstance(identity, ScientificIdentity) or identity.arm != "diagnostic":
        raise ValueError("Expected a diagnostic slot identity")
    if np.ndim(legal_outer_train_ids) != 1:
        raise ValueError("Expected a one-dimensional legal origin set")
    ids = tuple(value if isinstance(value, str) else operator.index(value) for value in legal_outer_train_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Legal origin set must be nonempty with unique origin IDs")

    def draw(index, side):
        key = (f"fgcs-v03|{identity.block}|{identity.entity}|{identity.fold}|"
               f"{identity.seed}|{identity.variant}|{index}|{side}")
        seed = int.from_bytes(sha256(key.encode("utf-8")).digest()[:8], "little")
        rng = np.random.Generator(np.random.PCG64(seed))
        indices = tuple(rng.integers(0, len(ids), size=BATCH_SIZE, dtype=np.int64).tolist())
        return Draw(key, indices, tuple(ids[i] for i in indices))

    return tuple(BatchPair(index, draw(index, "A"), draw(index, "B")) for index in range(PAIRS))
