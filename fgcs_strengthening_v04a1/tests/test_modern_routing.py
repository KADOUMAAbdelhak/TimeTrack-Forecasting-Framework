import unittest

from fgcs_strengthening_v04a1.src.modern.design import CONTEXTS, FAMILIES
from fgcs_strengthening_v04a1.src.models.registry import REGISTRY
from fgcs_strengthening_v04a1.src.modern.structure import validate_family_structure


class ModernRoutingTests(unittest.TestCase):
    def test_every_context_and_each_complement_path_passes_structural_validation(self):
        for family in FAMILIES:
            rows = validate_family_structure(family)
            scopes = REGISTRY[family].scopes
            self.assertEqual(len(rows), 15 * len(scopes))
            for scope, context in ((scope, context) for scope in scopes for context in CONTEXTS):
                paths = [row for row in rows if (row["scope"], row["context"]) == (scope, context)]
                self.assertEqual([len(row["tasks"]) for row in paths], [1, 1, 1, 1, 4])
                for row in paths:
                    self.assertEqual(row["output_shape"], [2, len(row["tasks"]), 5])
                    self.assertEqual(row["covered_lags"], list(range(context)))
                    if scope == "all":
                        self.assertEqual(row["channels"], 4)
                        self.assertTrue(all(all(flags) for flags in row["resource_to_target_dependencies"]))
                    if family == "iTransformer":
                        self.assertEqual(row["tokens"], 4)
                        self.assertEqual(row["variate_attention_dependencies"], [[True] * 4] * 4)
                        self.assertTrue(all(all(flags) for flags in row["resource_to_target_dependencies"]))
                    elif scope == "own":
                        channels = row["channels"]
                        self.assertEqual(row["resource_to_target_dependencies"],
                                         [[i == j for j in range(channels)] for i in range(channels)])
                        self.assertEqual(row["tokens"], context - 1 if family == "PatchTST" else None)

    def test_exact_parameter_counts_for_all_registered_contexts(self):
        expected = {
            "DLinear": ((50, 50), (100, 100), (190, 190)),
            "PatchTST": ((67653, 68628), (67973, 68948), (68549, 69524)),
            "iTransformer": ((68549, 72404), (68869, 72724), (69445, 73300)),
        }
        for family, counts in expected.items():
            checks = validate_family_structure(family)
            actual = tuple((checks[i]["parameter_count"], checks[i + 4]["parameter_count"]) for i in (0, 5, 10))
            self.assertEqual(actual, counts)
