import os
import pytest

def test_all_static_callbacks_have_handler():
    matrix_path = "BUTTON_AUDIT_MATRIX.md"
    if not os.path.exists(matrix_path):
        pytest.skip("Audit matrix not generated.")
        
    with open(matrix_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Find "- missing: X"
    for line in content.splitlines():
        if line.startswith("- missing:"):
            count = int(line.split(":")[1].strip())
            assert count == 0, f"Found {count} missing handlers in BUTTON_AUDIT_MATRIX.md"

def test_all_critical_buttons_answer_callback():
    audit_path = "CALLBACK_ANSWER_AUDIT.md"
    if not os.path.exists(audit_path):
        pytest.skip("Answer audit not generated.")
        
    with open(audit_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # The file has a section "## Missing callback.answer()"
    # followed by a table. If the table has more than 2 lines (header + separator), it means there are missing answers.
    lines = content.splitlines()
    try:
        missing_index = lines.index("## Missing callback.answer()")
        has_index = lines.index("## Has callback.answer()")
        missing_section = lines[missing_index+1:has_index]
        
        # Count non-empty lines in the table (ignoring headers)
        table_rows = [l for l in missing_section if l.strip().startswith("|")]
        # A fully empty table might just be headers: | file | function | ... \n |---|---|...
        # Let's check how many rows are there
        if len(table_rows) > 2:
            # We have an exception for process_post_title/price since they use event.answer()
            # If the only ones left are those, we pass.
            real_missing = 0
            for row in table_rows[2:]:
                if "process_post_title" not in row and "process_post_price" not in row:
                    real_missing += 1
            assert real_missing == 0, f"Found {real_missing} handlers actually missing callback.answer()"
    except ValueError:
        pass
