from dataclasses import replace
import json
import unittest

from fgcs_strengthening_v03.src.identity import RESOURCES, ScientificIdentity, canonical_json


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
            unit(), unit(seed=4), unit(phase="final"), unit(fold=2), unit(entity="860"),
            unit(formulation="M0", input_scope="own"),
            unit(formulation="M0", input_scope="own", arm="capacity", hidden_size=128),
            unit(formulation="S1", input_scope="own", tasks=("CPU",)),
            unit(formulation="S2", tasks=("CPU",)), unit(formulation="S2", tasks=("MEMORY",)),
            unit(arm="pairwise", tasks=("CPU", "MEMORY")),
            unit(arm="leave_one_out", tasks=("CPU", "MEMORY", "DISK_WRITE")),
            unit(arm="pcgrad", variant="pcgrad"), unit(arm="gradnorm", variant="gradnorm"),
            unit(arm="diagnostic", phase="final", variant="mid"),
            unit(arm="diagnostic", phase="final", variant="final"),
            unit(arm="checkpoint_request", phase="final", variant="task_selected", tasks=("CPU",)),
            unit(arm="modern", formulation="iTransformer", hidden_size=None, variant="shared"),
        ]
        self.assertEqual(len({identity.digest for identity in identities}), len(identities))

    def test_invalid_identities_fail_closed(self):
        for fields in ({"seed": True}, {"seed": 5}, {"fold": 0}, {"entity": "0697"}, {"entity": 697},
                       {"tasks": ("CPU", "CPU")}, {"input_scope": "own"}, {"variant": "retry"},
                       {"arm": "pcgrad", "variant": "pcgrad", "seed": 4},
                       {"arm": "modern", "formulation": "iTransformer", "variant": "shared",
                        "hidden_size": None, "input_scope": "own"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                replace(unit(), **fields)
