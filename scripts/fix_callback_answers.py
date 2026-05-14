import ast
import os
import glob

BASE = r"C:\Users\saymo\Цветочный-БОТ\telegram-order-button-bot"

def fix_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    source = "".join(lines)
    tree = ast.parse(source)
    
    modified = False
    
    class Fixer(ast.NodeTransformer):
        def visit_AsyncFunctionDef(self, node):
            is_callback = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and ast.unparse(dec.func).endswith("callback_query"):
                    is_callback = True
                    break
            
            if is_callback:
                # Find current callback.answer
                answer_node = None
                other_nodes = []
                for stmt in node.body:
                    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await):
                        call = stmt.value.value
                        if isinstance(call, ast.Call) and "callback.answer" in ast.unparse(call):
                            answer_node = stmt
                            continue
                    other_nodes.append(stmt)
                
                if answer_node:
                    # Move to top
                    node.body = [answer_node] + other_nodes
                    nonlocal modified
                    modified = True
                else:
                    # Insert at top if missing
                    new_answer = ast.Expr(value=ast.Await(value=ast.Call(
                        func=ast.Attribute(value=ast.Name(id='callback', ctx=ast.Load()), attr='answer', ctx=ast.Load()),
                        args=[], keywords=[]
                    )))
                    # Special check for cancel_order where it might be event/callback
                    # For now just insert callback.answer()
                    node.body = [new_answer] + node.body
                    modified = True
            
            return node

    # Transformer is a bit risky for complex code, let's use a simpler line-based approach
    # for the most common pattern.
    
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "@router.callback_query" in line:
            # Find function start
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("async def"):
                j += 1
            
            if j < len(lines):
                # Function found
                func_line = lines[j]
                # Check if it has callback: CallbackQuery
                if "callback:" in func_line or "cb:" in func_line:
                    # Find body start
                    k = j + 1
                    while k < len(lines) and ":" not in lines[j]: # wait, colon is on func_line
                        k += 1
                    
                    # Insert answer at k
                    indent = len(lines[k]) - len(lines[k].lstrip())
                    answer_call = " " * indent + "await callback.answer()\n"
                    
                    # But check if it already has it nearby
                    has_it = False
                    for m in range(k, min(k+5, len(lines))):
                        if "callback.answer()" in lines[m]:
                            has_it = True
                            break
                    
                    if not has_it:
                        lines.insert(k, answer_call)
                        modified = True
                        # Now remove any other callback.answer() in this function
                        # (Simpler to just let the user review)
        i += 1
    
    if modified:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    return False

# Manual fixes are better for high-stakes files.
# I'll just do it manually for the main handler files.
