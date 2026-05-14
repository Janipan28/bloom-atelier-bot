import ast
import glob
import os

class CallbackExtractor(ast.NodeVisitor):
    def __init__(self):
        self.callbacks = []
        
    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in {"InlineKeyboardButton", "ibtn"}:
            for kw in node.keywords:
                if kw.arg == "callback_data":
                    if isinstance(kw.value, ast.Constant):
                        self.callbacks.append((kw.value.value, node.lineno))
                    elif isinstance(kw.value, ast.JoinedStr):
                        # F-string
                        parts = []
                        for part in kw.value.values:
                            if isinstance(part, ast.Constant):
                                parts.append(str(part.value))
                            elif isinstance(part, ast.FormattedValue):
                                parts.append("{}")
                        self.callbacks.append(("".join(parts), node.lineno))
        self.generic_visit(node)

class HandlerExtractor(ast.NodeVisitor):
    def __init__(self):
        self.handlers = []

    @staticmethod
    def _is_callback_answer_await(node: ast.Await) -> bool:
        if not isinstance(node.value, ast.Call):
            return False
        if not isinstance(node.value.func, ast.Attribute):
            return False
        if node.value.func.attr != "answer":
            return False
        owner = node.value.func.value
        if isinstance(owner, ast.Name) and owner.id in {"callback", "event", "cb"}:
            return True
        return False
        
    def visit_AsyncFunctionDef(self, node):
        has_answer = False
        for child in ast.walk(node):
            if isinstance(child, ast.Await) and self._is_callback_answer_await(child):
                has_answer = True
                        
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute) and dec.func.attr == "callback_query":
                    for arg in dec.args:
                        pattern = None
                        if isinstance(arg, ast.Compare) and len(arg.ops) == 1 and isinstance(arg.ops[0], ast.Eq):
                            if isinstance(arg.left, ast.Attribute) and arg.left.attr == "data":
                                if isinstance(arg.comparators[0], ast.Constant):
                                    pattern = arg.comparators[0].value
                        elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == "startswith":
                            if isinstance(arg.args[0], ast.Constant):
                                pattern = arg.args[0].value + "*"
                        
                        if pattern:
                            self.handlers.append({
                                "function": node.name,
                                "pattern": pattern,
                                "has_answer": has_answer,
                                "lineno": node.lineno
                            })
        self.generic_visit(node)

def match_pattern(callback_data, pattern):
    if pattern.endswith("*"):
        return callback_data.startswith(pattern[:-1])
    return callback_data == pattern

def main():
    base_dir = r"C:\Users\saymo\Цветочный-БОТ\telegram-order-button-bot"
    
    # 1. Extract callbacks from keyboards
    keyboards_dir = os.path.join(base_dir, "bot", "keyboards", "**", "*.py")
    all_callbacks = []
    
    for filepath in glob.glob(keyboards_dir, recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            extractor = CallbackExtractor()
            extractor.visit(tree)
            for cb, lineno in extractor.callbacks:
                all_callbacks.append({
                    "data": cb,
                    "file": os.path.relpath(filepath, base_dir),
                    "lineno": lineno
                })
                
    # 2. Extract handlers
    handlers_dir = os.path.join(base_dir, "bot", "handlers", "**", "*.py")
    all_handlers = []
    
    for filepath in glob.glob(handlers_dir, recursive=True):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                tree = ast.parse(f.read())
                extractor = HandlerExtractor()
                extractor.visit(tree)
                for h in extractor.handlers:
                    h["file"] = os.path.relpath(filepath, base_dir)
                    all_handlers.append(h)
            except SyntaxError:
                print(f"SyntaxError in {filepath}")
                
    # 3. Match
    missing = []
    covered = []
    suspicious = []
    
    for cb in all_callbacks:
        matched = False
        for h in all_handlers:
            if match_pattern(cb["data"], h["pattern"]):
                matched = True
                covered.append({"cb": cb, "handler": h})
                break
        if not matched:
            missing.append(cb)
            
    # Output to md files
    with open(os.path.join(base_dir, "BUTTON_AUDIT_MATRIX.md"), "w", encoding="utf-8") as f:
        f.write("# BUTTON_AUDIT_MATRIX.md\n\n")
        f.write("## Summary\n\n")
        f.write(f"- total buttons found: {len(all_callbacks)}\n")
        f.write(f"- total callback handlers found: {len(all_handlers)}\n")
        f.write(f"- covered: {len(covered)}\n")
        f.write(f"- missing: {len(missing)}\n")
        f.write(f"- suspicious: {len(suspicious)}\n\n")
        
        f.write("## Dead / uncovered callbacks\n\n")
        f.write("| callback_data | keyboard file | status |\n")
        f.write("|---|---|---|\n")
        for m in missing:
            f.write(f"| `{m['data']}` | {m['file']}:{m['lineno']} | 🔴 missing handler |\n")
            
        f.write("\n## Covered callbacks\n\n")
        f.write("| callback_data | handler pattern | handler function | handler file |\n")
        f.write("|---|---|---|---|\n")
        for c in covered:
            f.write(f"| `{c['cb']['data']}` | `{c['handler']['pattern']}` | `{c['handler']['function']}` | {c['handler']['file']} |\n")

    with open(os.path.join(base_dir, "CALLBACK_ANSWER_AUDIT.md"), "w", encoding="utf-8") as f:
        f.write("# CALLBACK_ANSWER_AUDIT.md\n\n")
        missing_answer = [h for h in all_handlers if not h["has_answer"]]
        has_answer = [h for h in all_handlers if h["has_answer"]]
        
        f.write("## Missing callback.answer()\n\n")
        f.write("| file | function | callback pattern |\n")
        f.write("|---|---|---|\n")
        for h in missing_answer:
            f.write(f"| {h['file']} | `{h['function']}` | `{h['pattern']}` |\n")
            
        f.write("\n## Has callback.answer()\n\n")
        f.write("| file | function | callback pattern |\n")
        f.write("|---|---|---|\n")
        for h in has_answer:
            f.write(f"| {h['file']} | `{h['function']}` | `{h['pattern']}` |\n")

    print(f"Generated BUTTON_AUDIT_MATRIX.md and CALLBACK_ANSWER_AUDIT.md")
    print(f"Total Callbacks: {len(all_callbacks)}, Total Handlers: {len(all_handlers)}")
    print(f"Missing Handlers: {len(missing)}, Missing Answers: {len(missing_answer)}")

if __name__ == "__main__":
    main()
