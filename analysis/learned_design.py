"""The architecture and training constants of the learned estimator of section 6.

They live here, apart from the model itself, for one reason: `paper/collect_results.py` reads
them so the manuscript quotes the code rather than the author's memory, and it must be able to
do that in an environment where only `requirements-core.txt` is installed. Importing
`learned_estimator` pulls in torch, so a clean-copy verification of the release failed at this
import even though no number in the manuscript needs torch to be recomputed.

`learned_estimator.py` imports these names, so there is still one definition of each.
"""

from __future__ import annotations

TRACE_LENGTH = 128  #: every trace is resampled to this, so the model sees one input shape
HIDDEN = 256
EPOCHS = 40
BATCH = 256
TRAIN_SIZE = 60_000
TEST_PER_POINT = 2_000
ROOT_SEED = 20260906

#: The two conditions the protocol names. (b) is the fair test.
CONDITIONS = {
    "trained_above_the_bound": (2.5, 8.0),
    "trained_across_the_boundary": (0.5, 8.0),
}

TEST_CYCLES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0)
TOLERANCE = 0.05  #: same as step 3
