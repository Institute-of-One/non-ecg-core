"""Render the five body figures for Technology and Health Care.

    python paper/make_figures_thc.py

The journal asks for 300 dpi. `paper/figures.py` draws at 200 dpi, which is
the resolution the archived release contains and the resolution the article's
DOI points at, so it is not changed here: the same code draws the same picture
into `paper/build/figures_thc/` at 600 dpi instead, and half an inch of white
is added above each one because the submission portal puts a figure on a page
of its own and stamps its own label at the top left.

Nothing about the content changes. The data, the code and the drawing are the
ones in the release; only the raster density and the top margin differ, and
both are properties of the file rather than of the figure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt     # noqa: E402
import numpy as np                  # noqa: E402
from PIL import Image               # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "figures_thc"
DPI = 600
HEADROOM_IN = 0.5

# The body figures, in the order they appear, with the file each one writes.
BODY = [
    ("figure_window", "fig1_window.png", 1),
    ("figure_n_min", "fig2_n_min.png", 2),
    ("figure_protocols", "fig3_protocols.png", 3),
    ("figure_extraction", "fig4_extraction.png", 4),
    ("figure_flatness", "fig5_flatness.png", 5),
]


def pad_top(path: Path, dpi: int = DPI, inches: float = HEADROOM_IN) -> int:
    with Image.open(path) as im:
        want = int(round(inches * dpi))
        grey = np.asarray(im.convert("L"))
        ink = np.where((grey < 250).any(axis=1))[0]
        have = int(ink[0]) if ink.size else 0
        add = max(0, want - have)
        if add == 0:
            return 0
        white = (255,) * len(im.getbands())
        out = Image.new(im.mode, (im.width, im.height + add), white)
        out.paste(im, (0, add))
        out.save(path, dpi=(dpi, dpi))
    return add


def main() -> int:
    sys.path.insert(0, str(HERE))
    import figures as F

    OUT.mkdir(parents=True, exist_ok=True)
    F.FIGURES = OUT
    plt.rcParams.update({"figure.dpi": DPI, "savefig.dpi": DPI})

    for name, filename, number in BODY:
        builder = getattr(F, name)
        path = builder()
        if path.name != filename:
            raise SystemExit("%s wrote %s, expected %s" % (name, path.name, filename))
        target = OUT / ("Fig%d.png" % number)
        path.replace(target)
        added = pad_top(target)
        with Image.open(target) as im:
            print("Fig%d  %-24s %5d x %5d px, %.0f dpi, +%d px headroom"
                  % (number, filename, im.width, im.height,
                     (im.info.get("dpi") or (0, 0))[0], added))

    print("\n%d figure(s) in %s" % (len(BODY), OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
