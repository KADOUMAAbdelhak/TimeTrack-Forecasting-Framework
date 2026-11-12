"""Common v0.3 Transformer encoder construction."""

from torch import nn

from ..identity import read_config

SETTINGS = read_config()["modern"]["transformer"]


def make_encoder():
    layer = nn.TransformerEncoderLayer(
        d_model=SETTINGS["width"], nhead=SETTINGS["heads"],
        dim_feedforward=SETTINGS["feedforward"], dropout=SETTINGS["dropout"],
        activation=SETTINGS["activation"].lower(), batch_first=True,
        norm_first=SETTINGS["norm"] != "post", bias=SETTINGS["bias"],
    )
    return nn.TransformerEncoder(layer, num_layers=SETTINGS["layers"], enable_nested_tensor=False)
