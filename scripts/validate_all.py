from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = [
    ROOT / "scripts" / "validate_schema.py",
    ROOT / "scripts" / "validate_dataset.py",
    ROOT / "scripts" / "validate_central.py",
]

for script in SCRIPTS:
    print(f"== {script.name} ==", flush=True)
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
    if result.returncode:
        print(f"FAILED: {script.name}", file=sys.stderr)
        sys.exit(result.returncode)

print("all data validators passed")
