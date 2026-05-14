"""
Скрипт глубокого аудита: проверяет каждый callback handler логически.
Выводит матрицу: pattern | function | file | has_early_answer | has_db_before_answer | issues
"""
import ast
import glob
import os
import re

BASE = r"C:\Users\saymo\Цветочный-БОТ\telegram-order-button-bot"

class HandlerAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath, source):
        self.filepath = filepath
        self.source = source
        self.lines = source.splitlines()
        self.handlers = []

    def _lineno_to_source(self, lineno, count=5):
        start = max(0, lineno - 1)
        end = min(len(self.lines), lineno + count)
        return "\n".join(self.lines[start:end])

    def visit_AsyncFunctionDef(self, node):
        patterns = []
        is_callback_handler = False

        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr != "callback_query":
                continue
            is_callback_handler = True
            for arg in dec.args:
                self._extract_pattern(arg, patterns)
            for kw in dec.keywords:
                self._extract_pattern(kw.value, patterns)

        if not is_callback_handler:
            self.generic_visit(node)
            return

        # Analyze body
        body_stmts = node.body
        answer_first_line = None
        first_await_line = None
        has_db_before_answer = False
        has_answer = False
        db_calls_before_answer = []

        for i, stmt in enumerate(ast.walk(node)):
            if not isinstance(stmt, ast.Await):
                continue
            call = stmt.value
            if not isinstance(call, ast.Call):
                continue
            call_str = ast.unparse(call)
            lineno = getattr(stmt, "lineno", 0)

            # Check if this is callback.answer()
            is_answer = (
                "callback.answer" in call_str or
                "event.answer" in call_str
            )
            if is_answer and not has_answer:
                has_answer = True
                answer_first_line = lineno

            # Track DB/API calls before answer
            is_heavy = any(x in call_str for x in [
                "async_session", "session.get", "session.scalars",
                "session.execute", "session.scalar",
                "bot.send", "bot.get_me", "mm.show_menu",
                "notify_admin", "bot.delete",
            ])
            if is_heavy:
                if first_await_line is None:
                    first_await_line = lineno
                if not has_answer:
                    has_db_before_answer = True
                    db_calls_before_answer.append(call_str[:60])

        issues = []
        if not has_answer:
            issues.append("MISSING_ANSWER")
        elif has_db_before_answer:
            issues.append(f"ANSWER_LATE (DB before answer: {db_calls_before_answer[:2]})")

        if not patterns:
            patterns = ["<state_filtered>"]

        self.handlers.append({
            "file": os.path.relpath(self.filepath, BASE),
            "function": node.name,
            "patterns": patterns,
            "has_answer": has_answer,
            "answer_early": has_answer and not has_db_before_answer,
            "answer_late": has_answer and has_db_before_answer,
            "missing_answer": not has_answer,
            "issues": issues,
            "lineno": node.lineno,
        })

        self.generic_visit(node)

    def _extract_pattern(self, node, patterns):
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Attribute) and node.left.attr == "data":
                if node.comparators:
                    c = node.comparators[0]
                    if isinstance(c, ast.Constant):
                        patterns.append(f"== {c.value}")
        elif isinstance(node, ast.Call):
            fname = ast.unparse(node.func)
            if ".startswith" in fname or "startswith" in fname:
                if node.args and isinstance(node.args[0], ast.Constant):
                    patterns.append(f"startswith:{node.args[0].value}")
        elif isinstance(node, ast.Attribute) and node.attr == "data":
            patterns.append("<F.data>")


def analyze_all():
    handlers = []
    for filepath in glob.glob(os.path.join(BASE, "bot", "handlers", "**", "*.py"), recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            print(f"SyntaxError in {filepath}")
            continue
        analyzer = HandlerAnalyzer(filepath, source)
        analyzer.visit(tree)
        handlers.extend(analyzer.handlers)
    return handlers


handlers = analyze_all()

print(f"Total callback handlers: {len(handlers)}\n")

missing = [h for h in handlers if h["missing_answer"]]
late = [h for h in handlers if h["answer_late"]]
early = [h for h in handlers if h["answer_early"]]

print(f"✅ Early answer: {len(early)}")
print(f"⚠️  Late answer (DB before answer): {len(late)}")
print(f"❌ Missing answer: {len(missing)}\n")

if missing:
    print("=== MISSING callback.answer() ===")
    for h in missing:
        print(f"  {h['file']}:{h['lineno']} | {h['function']} | {h['patterns']}")

if late:
    print("\n=== LATE callback.answer() (will cause UI hang on slow DB) ===")
    for h in late:
        print(f"  {h['file']}:{h['lineno']} | {h['function']} | {h['patterns']}")
        for issue in h["issues"]:
            print(f"    ⚠️  {issue}")
