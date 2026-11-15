import unittest

from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.models.lstm import LSTM


class ParameterCountTests(unittest.TestCase):
    def test_m0_exact_trainable_counts_and_encoder_shape(self):
        for block, width, expected in (
            ("TimeTrack", 64, 52512), ("fastStorage", 64, 51732),
            ("TimeTrack", 128, 203296), ("fastStorage", 128, 201748),
        ):
            with self.subTest(block=block, width=width):
                model = LSTM(formulation="M0", block=block, tasks=RESOURCES, hidden_size=width)
                self.assertEqual(sum(p.numel() for p in model.parameters() if p.requires_grad), expected)
                self.assertEqual(model.encoder.input_size, 1)
                self.assertEqual(model.encoder.num_layers, 2)
                self.assertFalse(model.encoder.bidirectional)
                self.assertEqual(model.encoder.dropout, 0.1)
                self.assertEqual(tuple(model.heads), RESOURCES)
                self.assertTrue(all(head.bias is not None for head in model.heads.values()))

    def test_frozen_formulation_complements(self):
        for block, counts in (
            ("TimeTrack", (203808, 206880, 53280)),
            ("Materna-T3", (203028, 206100, 52500)),
        ):
            for formulation, expected in zip(("S1", "S2", "M1"), counts, strict=True):
                tasks = RESOURCES if formulation == "M1" else ("CPU",)
                model = LSTM(formulation=formulation, block=block, tasks=tasks, hidden_size=64)
                count = sum(p.numel() for p in model.parameters())
                self.assertEqual(count * (1 if formulation == "M1" else 4), expected)
