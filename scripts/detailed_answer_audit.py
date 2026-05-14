import ast
import os
import glob

BASE = r"C:\Users\saymo\Цветочный-БОТ\telegram-order-button-bot"

class DetailedAnalyzer(ast.NodeVisitor):
    def __init__(self, filepath, source):
        self.filepath = filepath
        self.source = source
        self.lines = source.splitlines()
        self.results = []

    def visit_AsyncFunctionDef(self, node):
        is_callback = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call) and "callback_query" in ast.unparse(dec.func):
                is_callback = True
                break
        
        if not is_callback: return

        # Find first answer and first await
        first_answer_line = None
        first_await_line = None
        
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Await):
                lineno = getattr(stmt, "lineno", 0)
                if first_await_line is None:
                    first_await_line = lineno
                
                call_str = ast.unparse(stmt.value)
                if "callback.answer" in call_str or "event.answer" in call_str or "cb.answer" in call_str:
                    if first_answer_line is None:
                        first_answer_line = lineno

        status = "OK"
        if first_answer_line is None:
            status = "MISSING"
        elif first_await_line < first_answer_line:
            status = "LATE"
            
        self.results.append({
            "func": node.name,
            "status": status,
            "line": node.lineno,
            "answer_line": first_answer_line,
            "first_await": first_await_line
        })

def analyze():
    files = glob.glob(os.path.join(BASE, "bot", "handlers", "*.py"))
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
        an = DetailedAnalyzer(fpath, src)
        an.visit(tree)
        if an.results:
            print(f"\n--- {os.path.basename(fpath)} ---")
            for r in an.results:
                print(f"[{r['status']}] {r['func']} (line {r['line']}, answer {r['answer_line']}, first_await {r['first_await']})")

if __name__ == "__main__":
    analyze()
