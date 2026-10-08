"""Create the data folders used by local development."""
from pathlib import Path

for folder in ("data/uploads", "data/processed", "data/knowledge", "data/chroma", "models"):
    Path(folder).mkdir(parents=True, exist_ok=True)
print("MRI Agent data folders are ready")
