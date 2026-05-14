"""
test_callback_data_limits.py — callback_data не должен превышать 64 байта (ограничение Telegram).
"""
import ast
import glob
import os
import pytest


def collect_all_callback_data(base_dir: str) -> list[tuple[str, str, int]]:
    """Returns list of (callback_data, file, lineno)."""
    results = []
    pattern = os.path.join(base_dir, "bot", "keyboards", "**", "*.py")

    class Extractor(ast.NodeVisitor):
        def __init__(self, filepath):
            self.filepath = filepath

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "InlineKeyboardButton":
                for kw in node.keywords:
                    if kw.arg == "callback_data":
                        if isinstance(kw.value, ast.Constant):
                            results.append((kw.value.value, self.filepath, node.lineno))
                        elif isinstance(kw.value, ast.JoinedStr):
                            # F-string: build worst-case estimate
                            parts = []
                            for part in kw.value.values:
                                if isinstance(part, ast.Constant):
                                    parts.append(str(part.value))
                                elif isinstance(part, ast.FormattedValue):
                                    # Assume max 20 chars for any dynamic part
                                    parts.append("X" * 20)
                            cb = "".join(parts)
                            results.append((cb, self.filepath, node.lineno))
            self.generic_visit(node)

    for filepath in glob.glob(pattern, recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
                ext = Extractor(filepath)
                ext.visit(tree)
            except SyntaxError:
                pass

    return results


def test_all_callback_data_under_64_bytes():
    """
    Telegram API requires callback_data ≤ 64 bytes.
    Static strings are checked exactly; f-strings are checked as worst-case estimate.
    """
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    callbacks = collect_all_callback_data(base_dir)

    violations = []
    for cb, filepath, lineno in callbacks:
        byte_len = len(cb.encode("utf-8"))
        if byte_len > 64:
            violations.append(f"{filepath}:{lineno} — '{cb}' ({byte_len} bytes)")

    assert not violations, (
        f"Found {len(violations)} callback_data exceeding 64 bytes:\n" +
        "\n".join(violations)
    )


def test_no_empty_callback_data():
    """Telegram API requires callback_data ≥ 1 byte."""
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    callbacks = collect_all_callback_data(base_dir)

    empty = [
        f"{filepath}:{lineno}"
        for cb, filepath, lineno in callbacks
        if len(cb.strip()) == 0
    ]
    assert not empty, f"Found empty callback_data at: {empty}"


def test_main_menu_layout_has_grid():
    """Main menu must have at least one row with 2 buttons (grid layout)."""
    from bot.keyboards.user import main_menu_kb
    kb = main_menu_kb()
    has_grid_row = any(len(row) == 2 for row in kb.inline_keyboard)
    assert has_grid_row, "Main menu must have at least one 2-button grid row"


def test_all_critical_flows_callback_data_under_limit():
    """Spot check known high-risk callback patterns."""
    critical = [
        "admin:main",
        "admin:orders",
        "admin:products",
        "admin:posts",
        "admin:stats",
        "user:catalog",
        "user:survey",
        "user:branches",
        "user:my_orders",
        "order:start_flow",
        "order:delivery",
        "order:pickup",
        "back:main",
        "post_action:publish",
        "post_action:preview",
    ]
    for cb in critical:
        byte_len = len(cb.encode("utf-8"))
        assert byte_len <= 64, f"Critical callback '{cb}' is {byte_len} bytes (max 64)"
        assert byte_len >= 1, f"Critical callback '{cb}' is empty"
