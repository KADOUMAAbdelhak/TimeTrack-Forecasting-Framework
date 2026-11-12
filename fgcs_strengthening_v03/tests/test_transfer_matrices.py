import unittest

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.transfer.design import prepare_bh_families, transfer_matrices


class MatrixTests(unittest.TestCase):
    def test_matrix_labels_roles_and_canonical_direction(self):
        matrices = tuple(transfer_matrices())
        self.assertEqual(len(matrices), 12)
        expected = [(target, source) for target in RESOURCES for source in RESOURCES if target != source]
        for matrix in matrices:
            self.assertEqual([(e.target_task, e.source_task) for e in matrix.entries], expected)
            for e in matrix.entries:
                self.assertIn(e.target_task, e.subset)
                self.assertEqual((e.block, e.scope), (matrix.block, matrix.scope))
                if matrix.arm == "pairwise":
                    self.assertEqual(set(e.subset), {e.target_task, e.source_task})
                    self.assertEqual(e.source_role, "sharing_partner")
                else:
                    self.assertEqual(set(e.subset), set(RESOURCES) - {e.source_task})
                    self.assertEqual(e.source_role, "omitted_supervision")
                if matrix.estimand == "Q":
                    self.assertEqual(e.comparator, "M0" if e.scope == "own" else "M1")
                    self.assertIn("adding source supervision", e.sign_convention)
                else:
                    self.assertEqual(e.comparator, "S1" if e.scope == "own" else "S2")
                    self.assertIn("favours sharing", e.sign_convention)

    def test_fixed_bh_slots_keep_unavailable_entries_and_exclude_q(self):
        matrices = tuple(transfer_matrices())
        first = matrices[0].entries[0].test_id
        families = prepare_bh_families({first: True})
        self.assertEqual(len(families), 8)
        self.assertEqual(len({family.matrix_id for family in families}), 8)
        all_ids = set()
        for family in families:
            self.assertEqual(family.q, .05)
            self.assertEqual(len(family.slots), 12)
            for slot in family.slots:
                self.assertEqual(slot.entry.estimand, "F")
                self.assertNotIn(slot.entry.test_id, all_ids)
                all_ids.add(slot.entry.test_id)
                self.assertEqual(slot.raw_p, None if slot.entry.test_id == first else 1)
        self.assertEqual(len(all_ids), 96)
        q = next(matrix.entries[0].test_id for matrix in matrices if matrix.estimand == "Q")
        with self.assertRaises(ValueError):
            prepare_bh_families({q: True})
