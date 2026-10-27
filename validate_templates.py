import os
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

print("Exhaustive Jinja Template Syntax Validation...")
has_error = False
for root, _, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            rel_path = os.path.relpath(os.path.join(root, f), 'templates').replace('\\', '/')
            try:
                env.get_template(rel_path)
                print(f"  [PASS] {rel_path}")
            except Exception as e:
                print(f"  [FAIL] {rel_path}: {e}")
                has_error = True

if has_error:
    print("\nTemplate validation FAILED.")
    exit(1)
else:
    print("\nAll templates PASSED with 0 syntax errors.")
