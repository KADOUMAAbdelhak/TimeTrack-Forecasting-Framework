from dataclasses import replace
import unittest

from fgcs_strengthening_v04.plan_execution import fit_identities
from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.transfer.design import (
    ARMS, LEAVE_ONE_OUT, PAIRWISE, dry_budget, group_identities, transfer_identities,
)


class TransferIdentityTests(unittest.TestCase):
    def test_six_unordered_pairs_and_four_omissions(self):
        self.assertEqual(PAIRWISE, (
            ("CPU", "THROUGHPUT"), ("CPU", "MEMORY"), ("CPU", "DISK_WRITE"),
            ("THROUGHPUT", "MEMORY"), ("THROUGHPUT", "DISK_WRITE"), ("MEMORY", "DISK_WRITE"),
        ))
        self.assertEqual(len(set(map(frozenset, PAIRWISE))), 6)
        self.assertEqual(len(set(LEAVE_ONE_OUT)), 4)
        self.assertEqual([next(iter(set(RESOURCES) - set(tasks))) for tasks in LEAVE_ONE_OUT], list(RESOURCES))

    def test_pair_identity_canonicalises_task_order_and_rejects_outside_scope(self):
        pair = next(group_identities("fastStorage", "697", 1, 0, "inner"))
        reversed_pair = replace(pair, tasks=pair.tasks[::-1])
        self.assertEqual(pair.payload(), reversed_pair.payload())
        self.assertEqual(pair.digest, reversed_pair.digest)
        for change in ({"seed": 3}, {"hidden_size": 128}, {"variant": "pilot"},
                       {"block": "TimeTrack", "entity": "machine01"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(pair, **change)

    def test_transfer_and_full_dry_planners_have_the_same_identity_set(self):
        transfer = set(transfer_identities())
        self.assertEqual(transfer, {i for i in fit_identities() if i.arm in ARMS})
        self.assertEqual(len(transfer), 42000)
        self.assertEqual(dry_budget(), {"pairwise": {"inner": 12600, "final": 12600},
                                       "leave_one_out": {"inner": 8400, "final": 8400}})
        for block in ("fastStorage", "Rnd"):
            self.assertEqual(len({i.entity for i in transfer if i.block == block}), 35)
        self.assertEqual({i.seed for i in transfer}, {0, 1, 2})
