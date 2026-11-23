"""Amendment A3 pre-freeze check (run once before the freeze; PYTHONPATH=repository root): readers and reproduction guards only; no policy, oracle or detection statistic."""
import time
import numpy as np
from fgcs_strengthening_v04a3 import analyse_gate as a
t=time.time()
loaded=[a.tier1_frame(b, a.CONFIG["tier1"]["blocks"][b]) for b in a.TIER1_BLOCKS]
print("tier1 worst relative difference", a.tier1_guard(loaded))
for f,_ in loaded: print(f.block, f.shape, sorted(f.val))
frames, hashes = a.tier2_frames()
from fgcs_strengthening_v04.src.analysis.bootstrap import Draws
print("tier2 contrasts reproduced exactly:", a.tier2_guard(frames, Draws()))
for f in frames: print(f.block, f.backbone, f.shape, len(f.val), f.val_p.shape, np.isfinite(f.val_p).all())
print(round(time.time()-t), "s")
