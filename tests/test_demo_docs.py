"""Keep examples/demo.py in step with the widget's helpers.

Every public helper on LightweightChartWidget must be both used in the demo's
code and explained in its markdown. When this fails after adding or renaming a
helper, add an example and a markdown explanation to the demo (see CLAUDE.md).
"""

import ast
from pathlib import Path

import pytest

from tradingview_anywidget import LightweightChartWidget

DEMO = Path(__file__).parent.parent / "examples" / "demo.py"

# Helpers covered by another one in the demo
NOT_SHOWN = {
    "markers",  # alias of marker()
    "dark_theme",  # shown through W.theme("dark")
    "light_theme",  # shown through W.theme("light")
}

HELPERS = sorted(
    name
    for name, value in vars(LightweightChartWidget).items()
    if isinstance(value, staticmethod) and not name.startswith("_") and name not in NOT_SHOWN
)


def _demo_tree():
    return ast.parse(DEMO.read_text())


def _helpers_called_in_code(tree):
    """Names of W.<name>(...) calls in the demo."""
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "W"
    }


def _markdown_text(tree):
    """All text passed to mo.md(...) in the demo."""
    parts = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "md"
            and node.args
        ):
            for sub in ast.walk(node.args[0]):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    parts.append(sub.value)
    return "\n".join(parts)


@pytest.mark.parametrize("helper", HELPERS)
def test_helper_is_used_in_demo(helper):
    assert helper in _helpers_called_in_code(_demo_tree()), f"W.{helper}() has no example in examples/demo.py"


@pytest.mark.parametrize("helper", HELPERS)
def test_helper_is_explained_in_demo_markdown(helper):
    assert f"W.{helper}(" in _markdown_text(_demo_tree()), (
        f"W.{helper}() is not explained in any mo.md() cell in examples/demo.py"
    )
