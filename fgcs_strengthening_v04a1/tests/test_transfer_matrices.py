import unittest

from fgcs_strengthening_v04a1.src.identity import RESOURCES
from fgcs_strengthening_v04a1.src.transfer.design import transfer_matrices


class MatrixTests(unittest.TestCase):
    def test_matrix_labels_roles_and_canonical_direction(self):
        matrices = tuple(transfer_matrices())
        # v0.4: two blocks, all-input scope only, three matrices (pairwise F, leave-one-out F and Q).
        self.assertEqual(len(matrices), 6)
        self.assertEqual({m.scope for m in matrices}, {"all"})
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


if __name__ == "__main__":
    unittest.main()
