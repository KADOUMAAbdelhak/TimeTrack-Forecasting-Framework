"""Journal one registered diagnostic slot from a completed core (v0.4) or intervention (A1) final fit."""

import io
from pathlib import Path
from time import perf_counter

import torch

from ..checkpoints import diagnostic_slots
from ..data_adapters import PreparedPartition
from ..identity import ROOT, ScientificIdentity, diagnostic_parent, diagnostic_slot
from ..provenance import Fingerprints, Journal, ProvenanceError
from ..training import _SOURCE_FILES, _state_hash, _windows
from .batches import build_batch_pairs, json_sha256
from .gradients import PARAMETERS, DiagnosticClone, StateContamination, live_state_hashes
from .metrics import pair_metrics, slot_metrics

_SOURCES = (*_SOURCE_FILES, *(
    Path(__file__).resolve().with_name(name).relative_to(ROOT).as_posix()
    for name in ("engine.py", "batches.py", "gradients.py", "metrics.py", "aggregation.py")
))


def diagnostic_fingerprints():
    """Use this seal for both the parent training journal and its diagnostics."""
    return Fingerprints.capture_protocol(additional_sources=_SOURCES)


class DiagnosticEngine:
    def __init__(self, journal):
        if not isinstance(journal, Journal):
            raise TypeError("Expected the final fit's Stage 3A journal")
        journal.seal.require_protocol(additional_sources=_SOURCES)
        self.journal = journal

    def run(self, identity, partition, live_model, optimizer, shuffle_generator):
        if not isinstance(identity, ScientificIdentity) or identity.arm != "diagnostic":
            raise ValueError("Expected a diagnostic identity")
        if not isinstance(partition, PreparedPartition) or (
            partition.block, partition.entity, partition.fold, partition.phase
        ) != (identity.block, identity.entity, identity.fold, "final"):
            raise ProvenanceError("Expected the matching final fit's outer-training partition")

        parent = diagnostic_parent(identity)
        final, final_hash = self.journal.completed_evidence(parent)
        metadata = {"context": partition.context, "support_sha256": partition.support_sha256,
                    "split_hashes": dict(partition.split_hashes), "scaler_sha256": partition.scaler_sha256,
                    "configuration_sha256": self.journal.seal.configuration[1]}
        if any(final.get(key) != value for key, value in metadata.items()):
            raise ProvenanceError("Partition fingerprint differs from the parent final fit")
        joint = final["selection"]["joint_epoch"]
        slots = diagnostic_slots(joint)
        if final.get("diagnostic_slots") != slots or final.get("primary_checkpoint_epoch") != joint:
            raise ProvenanceError("Final fit lacks the registered diagnostic checkpoint schedule")

        slot_name = diagnostic_slot(identity)
        epoch = slots[slot_name]
        shared = [slot for slot, value in slots.items() if value == epoch]
        primary = identity.formulation == "M1" and slot_name == "final"
        evidence = {**metadata, "final_identity": parent.payload(), "final_identity_sha256": parent.digest,
                    "final_outcome_sha256": final_hash, "joint_epoch": joint,
                    "slot": slot_name, "epoch": epoch, "is_primary": primary,
                    "slots_at_same_epoch": shared, "duplicate_checkpoint_epoch": len(shared) > 1,
                    "encoder_parameters": list(PARAMETERS), "pairs": []}
        if parent.arm == "intervention":
            # A1 manipulation check: the parent's task weights after the checkpoint epoch.
            if epoch < 1 or final["epochs"][epoch - 1]["epoch"] != epoch:
                raise ProvenanceError("Intervention diagnostic needs a trained checkpoint epoch")
            evidence["loss_mode"] = final["loss_mode"]
            evidence["loss_weights"] = dict(final["epochs"][epoch - 1]["loss_weights"])
        attempt = self.journal.start(identity)
        start = perf_counter()
        try:
            evidence["live_before"] = live_state_hashes(live_model, optimizer, shuffle_generator)
            try:
                reference = final.get("diagnostic_checkpoints", {}).get(str(epoch))
                if reference is None:
                    raise ProvenanceError("Final fit lacks the required diagnostic checkpoint")
                evidence["checkpoint"] = reference
                if epoch == joint and reference != final["checkpoints"][str(joint)]:
                    raise ProvenanceError("Joint diagnostic and primary deployment checkpoints differ")
                self._compute(identity, parent, partition, live_model, epoch, reference, evidence)
                summary = slot_metrics(evidence["pairs"])
            finally:
                evidence["live_after"] = live_state_hashes(live_model, optimizer, shuffle_generator)
                changed = [key for key, digest in evidence["live_before"].items()
                           if evidence["live_after"][key] != digest]
                evidence["changed_live_state"] = changed
                if changed:
                    raise StateContamination(f"Diagnostic changed live state: {', '.join(changed)}")
            evidence["summary"] = summary
            evidence["primary_K"] = summary["K"] if primary else None
            evidence["availability"] = "complete" if summary["K"] is not None else "unavailable_zero_gradient"
        except Exception as error:
            evidence["diagnostic_seconds"] = perf_counter() - start
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            self.journal.finish(attempt, status="failed", evidence=evidence)
            raise
        evidence["diagnostic_seconds"] = perf_counter() - start
        self.journal.finish(attempt, status="complete", evidence=evidence)
        return evidence

    def _compute(self, identity, parent, partition, live_model, epoch, reference, evidence):
        if (live_model.formulation != identity.formulation
                or live_model.encoder.hidden_size != identity.hidden_size):
            raise ProvenanceError("Live architecture differs from the final-fit identity")
        encoded = self.journal.checkpoint_bytes(parent, epoch, reference)
        state = torch.load(io.BytesIO(encoded), map_location="cpu", weights_only=True)
        if _state_hash(state) != reference["model_sha256"]:
            raise ProvenanceError("Checkpoint model tensors differ from the final-fit record")
        clone = DiagnosticClone(live_model, state)
        windows = partition.training()
        inputs, targets = _windows(windows, identity, partition.context)
        pairs = build_batch_pairs(identity, windows.origin_ids)
        manifest = {"slot_identity_sha256": identity.digest, "outer_train_sha256": partition.split_hashes["outer_train"],
                    "ordered_legal_ids_sha256": json_sha256(windows.origin_ids.tolist()),
                    "pairs": [pair.payload() for pair in pairs]}
        evidence["batch_manifest"] = manifest
        evidence["batch_manifest_sha256"] = json_sha256(manifest)
        for pair in pairs:
            gradients = {}
            for side in ("A", "B"):
                evidence["active_draw"] = {"pair_index": pair.index, "side": side}
                rows = list(getattr(pair, side).indices)
                gradients[side] = clone.extract(inputs[rows], targets[rows])
            evidence["pairs"].append({"pair_index": pair.index, **pair_metrics(gradients["A"], gradients["B"])})
        evidence.pop("active_draw")
