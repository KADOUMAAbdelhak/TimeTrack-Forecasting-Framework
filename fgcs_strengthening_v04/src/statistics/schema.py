"""Provenance-required v0.3 result rows with JSON-safe extended values."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
import re
from types import MappingProxyType

from ..identity import canonical_json
from .bootstrap import Inference
from .design import AnalysisSlot

_DIGEST = re.compile(r"[0-9a-f]{64}")


def is_sha256(value):
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _hash_map(mapping):
    if not mapping or any(not isinstance(path, str) or not path or not is_sha256(value)
                          for path, value in mapping.items()):
        raise ValueError("Expected nonempty path-to-SHA-256 provenance")
    return MappingProxyType(dict(sorted(mapping.items())))


@dataclass(frozen=True, slots=True)
class Provenance:
    protocol_sha256: str
    config_sha256: str
    source_hashes: dict
    input_hashes: dict

    def __post_init__(self):
        if not is_sha256(self.protocol_sha256) or not is_sha256(self.config_sha256):
            raise ValueError("Protocol and configuration SHA-256 are required")
        for field in ("source_hashes", "input_hashes"):
            object.__setattr__(self, field, _hash_map(getattr(self, field)))

    def hashes(self):
        return {"protocol_sha256": self.protocol_sha256, "config_sha256": self.config_sha256,
                "source_sha256": sha256(canonical_json(dict(self.source_hashes))).hexdigest(),
                "input_sha256": sha256(canonical_json(dict(self.input_hashes))).hexdigest()}

    def payload(self):
        return {**self.hashes(), "source_hashes": dict(self.source_hashes), "input_hashes": dict(self.input_hashes)}


def extended_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            raise ValueError("Undefined values must be represented as null")
        return "+inf" if value > 0 else "-inf"
    if isinstance(value, dict):
        return {key: extended_json(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [extended_json(child) for child in value]
    return value


@dataclass(frozen=True, slots=True)
class AnalysisRow:
    slot: AnalysisSlot
    inference: Inference
    provenance: Provenance
    support_status: str
    zero_counts: dict
    missing_counts: dict
    details: dict
    adjusted_p: float | None = None
    rejected: bool | None = None
    supports_direction: bool | None = None

    def __post_init__(self):
        if not isinstance(self.provenance, Provenance):
            raise ValueError("Analysis row requires validated provenance")
        if not isinstance(self.slot, AnalysisSlot) or not isinstance(self.inference, Inference):
            raise ValueError("Analysis row requires a registered slot and result")
        if (not self.slot.cohort or not self.slot.seeds or not self.slot.reference_seeds or not self.slot.blocks
                or not self.slot.context_rule or self.support_status not in {"complete", "incomplete"}
                or any(type(n) is not int or n < 0 for counts in (self.zero_counts, self.missing_counts)
                       for n in counts.values())):
            raise ValueError("Incomplete cohort, support or accounting metadata")
        if self.slot.inferential:
            if self.slot.environment == "TimeTrack" or self.slot.correction not in {"Holm", "BH"}:
                raise ValueError("Invalid inferential scope or correction")
            for value in (self.inference.raw_p, self.adjusted_p):
                if value is None or type(value) is bool or not 0 <= value <= 1:
                    raise ValueError("Inferential rows require finite raw and adjusted p-values")
            if self.inference.point is None:
                if self.inference.raw_p != 1 or self.adjusted_p != 1:
                    raise ValueError("An unavailable test must retain p=1")
            elif not math.isfinite(self.inference.point):
                raise ValueError("Inferential point estimates must be finite")
        elif any(value is not None for value in (self.inference.raw_p, self.adjusted_p, self.rejected)):
            raise ValueError("Descriptive rows cannot carry hypothesis-test results")
        if (not self.slot.interval or self.slot.environment == "TimeTrack") and (
                self.inference.ci is not None or self.inference.ratio_ci is not None):
            raise ValueError("Intervals are outside this descriptive slot's scope")

    def payload(self):
        row = asdict(self.slot)
        row.update(asdict(self.inference), **self.provenance.hashes(),
                   n_entities=len(self.slot.cohort), support_status=self.support_status,
                   zero_counts=self.zero_counts, missing_counts=self.missing_counts, details=self.details,
                   adjusted_p=self.adjusted_p, rejected=self.rejected, supports_direction=self.supports_direction,
                   analysis_type="inferential" if self.slot.inferential else "descriptive",
                   correction_family=self.slot.family)
        row["point_estimate"] = row.pop("point")
        row["sign_convention"] = self.slot.transfer.sign_convention if self.slot.transfer else {
            "D": "positive means higher candidate error",
            "I": "positive means a greater sharing penalty under all-input sharing",
            "Spearman": "positive associates larger excess conflict with larger sharing penalties",
            "R_persist": "above one means higher model error relative to persistence",
        }[self.slot.estimand]
        return extended_json(row)
