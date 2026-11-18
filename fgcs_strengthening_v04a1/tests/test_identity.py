from dataclasses import replace
import json
import unittest

from fgcs_strengthening_v04a1.src.identity import RESOURCES, ScientificIdentity, canonical_json


def unit(**changes):
    fields = dict(block="fastStorage", entity="697", fold=1, seed=0, phase="inner",
                  arm="core", formulation="M1", tasks=RESOURCES, input_scope="all",
                  hidden_size=64, variant="baseline")
    return ScientificIdentity(**(fields | changes))


class IdentityTests(unittest.TestCase):
    def test_canonical_payload_round_trip(self):
        identity = unit()
        payload = json.loads(canonical_json(identity.payload()))
        payload.pop("namespace")
        payload.pop("schema_version")
        restored = ScientificIdentity(**payload)
        self.assertEqual(restored.digest, identity.digest)
        self.assertEqual(identity.digest, unit(tasks=tuple(reversed(RESOURCES))).digest)

    def test_seed_phase_target_scope_and_arm_distinguish_identities(self):
        identities = [
            unit(), unit(seed=2), unit(phase="final"), unit(fold=2), unit(entity="860"),
            unit(formulation="M0", input_scope="own"),
            unit(formulation="S1", input_scope="own", tasks=("CPU",)),
            unit(formulation="S2", tasks=("CPU",)), unit(formulation="S2", tasks=("MEMORY",)),
            unit(arm="pairwise", tasks=("CPU", "MEMORY")),
            unit(arm="leave_one_out", tasks=("CPU", "MEMORY", "DISK_WRITE")),
            unit(arm="diagnostic", phase="final", variant="final"),
            unit(arm="modern", formulation="iTransformer", hidden_size=None, variant="shared"),
            unit(arm="modern", formulation="DLinear", hidden_size=None, variant="shared"),
            unit(arm="modern", formulation="DLinear", hidden_size=None, variant="shared", input_scope="own"),
            unit(arm="modern", formulation="PatchTST", hidden_size=None, variant="independent", tasks=("CPU",)),
            unit(arm="modern", formulation="PatchTST", hidden_size=None, variant="independent", tasks=("CPU",),
                 input_scope="own"),
        ]
        self.assertEqual(len({identity.digest for identity in identities}), len(identities))

    def test_invalid_identities_fail_closed(self):
        for fields in ({"seed": True}, {"seed": 3}, {"fold": 0}, {"entity": "0697"}, {"entity": 697},
                       {"entity": "434"},  # a fastStorage VM outside the 20-VM cohort
                       {"block": "TimeTrack", "entity": "machine01"}, {"tasks": ("CPU", "CPU")},
                       {"input_scope": "own"}, {"variant": "retry"}, {"hidden_size": 128},
                       {"arm": "capacity", "formulation": "M0", "input_scope": "own", "hidden_size": 128},
                       {"arm": "pcgrad", "variant": "pcgrad"}, {"arm": "lightgbm"},
                       {"arm": "checkpoint_request", "phase": "final", "variant": "task_selected", "tasks": ("CPU",)},
                       {"arm": "diagnostic", "phase": "final", "variant": "mid"},
                       {"arm": "pairwise", "formulation": "M0", "input_scope": "own", "tasks": ("CPU", "MEMORY")},
                       {"arm": "modern", "formulation": "iTransformer", "variant": "shared",
                        "hidden_size": None, "input_scope": "own"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                replace(unit(), **fields)

    def test_modern_cells_map_to_the_2x2(self):
        cells = {(scope, variant): unit(arm="modern", formulation="DLinear", hidden_size=None, variant=variant,
                                         input_scope=scope, tasks=RESOURCES if variant == "shared" else ("CPU",)).cell
                 for scope in ("own", "all") for variant in ("independent", "shared")}
        self.assertEqual(cells, {("own", "independent"): "S1", ("all", "independent"): "S2",
                                 ("own", "shared"): "M0", ("all", "shared"): "M1"})
        self.assertEqual(unit(formulation="S2", tasks=("CPU",)).cell, "S2")
        self.assertIsNone(unit(arm="pairwise", tasks=("CPU", "MEMORY")).cell)
