# Phase 4B non-scientific pilot

Every artifact in this directory is a technical preflight artifact. The pilot used only the frozen first cohort member in each environment, outer fold 1 metadata, seed 0, context 9, and the inner-training and inner-validation partitions for exactly five epochs.

The pilot did not load outer-test target arrays, generate outer-test predictions, select a scientific context, perform a final refit, test H1/H2/H3, or produce scientific evidence. Its validation metrics exist only to check transforms, inversion, target ordering, numerical finiteness, timing, memory, and storage assumptions. They must not be used for model or environment comparisons.

