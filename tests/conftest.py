import os
import sys
from pathlib import Path

# Get the absolute path to the project root
project_root = str(Path(__file__).parent.parent.absolute())
print("Adding to path:", project_root)

# Add the project root to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)