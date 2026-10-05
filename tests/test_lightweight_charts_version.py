"""Flag when the lightweight-charts submodule has a newer release than the widget uses.

The submodule tracks TradingView's master branch. Its package.json version is
bumped when TradingView publishes a release, so after pulling a new release
this test fails until chart.js imports that major.minor version from the CDN.
See "Update lightweight-charts" in README.md for the upgrade steps.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SUBMODULE_PACKAGE = ROOT / "lightweight-charts" / "package.json"
CHART_JS = ROOT / "src" / "lightweight_charts_anywidget" / "chart.js"


@pytest.mark.skipif(not SUBMODULE_PACKAGE.exists(), reason="lightweight-charts submodule not checked out")
def test_cdn_version_matches_latest_lightweight_charts_release():
    released = json.loads(SUBMODULE_PACKAGE.read_text())["version"]
    released_minor = ".".join(released.split(".")[:2])
    pinned = re.search(r"esm\.sh/lightweight-charts@([\d.]+)", CHART_JS.read_text()).group(1)
    assert pinned == released_minor, (
        f"lightweight-charts {released} is out but chart.js imports @{pinned}. "
        f"Bump the CDN import to @{released_minor}, read the release notes in "
        "lightweight-charts/website/docs/release-notes.md, and re-test the demo."
    )
