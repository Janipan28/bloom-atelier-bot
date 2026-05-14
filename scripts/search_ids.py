import os
import re

def main():
    pattern = re.compile(r'-100\d{8,}')
    for root, dirs, files in os.walk('.'):
        if '.venv' in dirs: dirs.remove('.venv')
        if '.git' in dirs: dirs.remove('.git')
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    if matches:
                        print(f"FOUND IN {path}: {matches}")
            except:
                pass

if __name__ == "__main__":
    main()
