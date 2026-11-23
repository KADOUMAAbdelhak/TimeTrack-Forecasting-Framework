"""Synthetic tests of the A3 policies, outcomes and verdicts (no real data is read)."""

import numpy as np
import pytest

from fgcs_strengthening_v04a3 import analyse_gate, gate
from fgcs_strengthening_v04a3.gate import RESOURCES, Frame

E, F, S, R, H = 4, 2, 3, 4, 2


def frame(*, lattice=False, persistence=False, seed=0):
    rng = np.random.default_rng(seed)
    cells = ["S1", "S2", "M0", "M1"] + ([gate.group_cell(g) for p in gate.partitions() for g in p
                                         if 1 < len(g) < 4] if lattice else [])
    cells = list(dict.fromkeys(cells))
    val, outer, params = {}, {}, {}
    for cell in cells:
        val[cell] = rng.uniform(0.5, 1.5, size=(E, F, S, R))
        outer[cell] = rng.uniform(1.0, 2.0, size=(E, F, S, R, H))
        if cell.startswith("M1/"):
            covered = [RESOURCES.index(t) for t in cell[3:].split("+")]
            mask = np.ones(R, dtype=bool)
            mask[covered] = False
            val[cell][..., mask] = np.nan
            outer[cell][..., mask, :] = np.nan
        params[cell] = np.full((E, F, S, R), 10.0 if cell in ("S1", "S2") else 25.0)
    extra = {}
    if persistence:
        extra = {"val_p": rng.uniform(0.5, 1.5, size=(E, F, R)), "outer_p": rng.uniform(1.0, 2.0, size=(E, F, R, H))}
    return Frame("tier2", "fastStorage", "LSTM", tuple(f"vm{i}" for i in range(E)), val, outer, params, **extra)


def draws():
    return analyse_gate.BlockDraws({"fastStorage": E}, replicates=200)


def test_partitions_are_the_fifteen_set_partitions():
    found = gate.partitions()
    assert len(found) == 15 and len(set(found)) == 15
    assert found[0] == (RESOURCES,)
    assert found[-1] == tuple((r,) for r in RESOURCES)
    assert gate.partition_cells(found[0]) == ("M1",) * 4
    assert gate.partition_cells(found[-1]) == ("S2",) * 4
    assert sorted(len(p) for p in found) == [1] + [2] * 7 + [3] * 6 + [4]


def test_models_and_params_count_independent_targets_separately():
    f = frame()
    models, params = gate.models_and_params(f, gate.fixed(f, "S2"))
    assert (models == 4).all() and (params == 40).all()
    models, params = gate.models_and_params(f, gate.fixed(f, "M1"))
    assert (models == 1).all() and (params == 25).all()
    mixed = gate.fixed(f, "S2")
    mixed[..., 0] = gate.PERSISTENCE
    models, _ = gate.models_and_params(f, mixed)
    assert (models == 3).all()


def test_g_share_consolidates_within_tolerance_only():
    f = frame()
    f.val["S2"][:] = 1.0
    f.val["M1"][:] = 1.0
    f.val["M1"][0] = 1.02  # first VM: 2 % worse on validation
    for tolerance, first in ((0.01, "S2"), (0.02, "M1")):
        a = gate.g_share(f, tolerance)
        assert (a[0] == first).all() and (a[1:] == "M1").all()


def test_g_ctx_prefers_s1_on_ties():
    f = frame()
    f.val["S2"][:] = f.val["S1"]
    assert (gate.g_ctx(f) == "S1").all()
    f.val["S2"][..., 2] = f.val["S1"][..., 2] - 0.1
    a = gate.g_ctx(f)
    assert (a[..., 2] == "S2").all() and (a[..., [0, 1, 3]] == "S1").all()


def test_g_group_takes_fewest_models_among_feasible():
    f = frame(lattice=True)
    for cell in f.val:
        f.val[cell] = np.where(np.isnan(f.val[cell]), np.nan, 1.5)
    f.val["S2"][:] = 1.0
    pair = "M1/CPU+THROUGHPUT", "M1/MEMORY+DISK_WRITE"
    for cell in pair:
        f.val[cell] = np.where(np.isnan(f.val[cell]), np.nan, 1.0)
    a = gate.g_group(f, 0.0)
    assert (a[..., :2] == pair[0]).all() and (a[..., 2:] == pair[1]).all()
    f.val["M1"][:] = 1.0  # now the single shared model is feasible and has fewer models
    assert (gate.g_group(f, 0.0) == "M1").all()
    for cell in f.val:
        if cell != "S2":
            f.val[cell] = f.val[cell] + 1
    assert (gate.g_group(f, 0.02) == "S2").all()


def test_fallback_and_outer_gathering():
    f = frame(persistence=True)
    f.val_p[:] = 10.0
    f.val_p[:, :, 1] = 0.0
    a = gate.with_fallback(f, gate.fixed(f, "S2"))
    assert (a[..., 1] == gate.PERSISTENCE).all() and (a[..., [0, 2, 3]] == "S2").all()
    out = gate.policy_outer(f, a)
    assert np.array_equal(out[..., 1, :], np.broadcast_to(f.outer_p[:, :, None, 1, :], out[..., 1, :].shape))
    assert np.array_equal(out[..., 0, :], f.outer["S2"][..., 0, :])


def test_fixed_policy_rows_match_matched_descriptives():
    f = frame(persistence=True)
    rows, summary = gate.accuracy_rows(f, "M1", gate.fixed(f, "M1"), draws())
    for r, row in enumerate(rows):
        expected = gate.matched_descriptives(gate.seed_mean(f.outer["M1"], r), gate.seed_mean(f.outer["S2"], r))
        assert row["median_ratio_vs_S2"] == expected["median_ratio"]
        assert row["median_ratio_vs_M1"] == 1.0
    assert summary["mean_models"] == 1 and summary["mean_parameters"] == 25


def test_detection_on_aligned_and_reversed_scores():
    f = frame()
    f.outer["S2"][:] = 1.0
    f.val["S2"][:] = 1.0
    score = np.linspace(0.8, 1.2, E * F * S).reshape(E, F, S)
    f.val["M1"][:] = score[..., None]
    f.outer["M1"][:] = score[..., None, None]
    d = gate.detection(f, draws())
    assert d["rho"] == pytest.approx(1.0) and gate.detection_verdict(d) == "detects"
    f.outer["M1"][:] = (2 - score)[..., None, None]
    assert gate.detection_verdict(gate.detection(f, draws())) == "does not detect"


def test_verdict_boundaries():
    assert gate.h_a3a_verdict(0.5, 6, 13) == "keeps most savings at reduced cost"
    assert gate.h_a3a_verdict(0.5, 7, 13) == "does not avoid the cost"
    assert gate.h_a3a_verdict(0.2, 0, 13) == "rarely consolidates"
    assert gate.h_a3a_verdict(0.3, 11, 22) == "keeps some savings at reduced cost"
    assert gate.h_a3c_verdict(2.0, 2.2, 3, 2) == "no added savings"
    assert gate.h_a3c_verdict(1.9, 2.2, 3, 2) == "grouping adds savings"
    assert gate.h_a3c_verdict(1.9, 2.2, 4, 2) == "adds savings at a cost"
    assert gate.fallback_verdict(8).startswith("fallback restores")
    assert gate.savings_retained(2.5, 4, 1) == pytest.approx(0.5)


def test_all_policies_run_on_a_lattice_frame():
    f = frame(lattice=True, persistence=True)
    names = [name for name, _ in analyse_gate.frame_policies(f)]
    assert len(names) == len(set(names))
    assert "G-group@1%" in names and "G-share@1%+fallback" in names and len([n for n in names if n.startswith("partition:")]) == 15
    for name, assignment in analyse_gate.frame_policies(f):
        gate.policy_outer(f, assignment)


def test_dry_plan_reads_no_data():
    plan = analyse_gate.dry_plan()
    assert plan["fits"] == 0 and plan["partitions"] == 15 and plan["primary_tolerance"] == 0.01


def test_every_policy_assigns_every_resource():
    f = frame(lattice=True, persistence=True)
    for name, assignment in analyse_gate.frame_policies(f):
        assert assignment.shape == (E, F, S, R), name
