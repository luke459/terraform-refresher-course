from dataclasses import dataclass
from pathlib import Path
import os
import shutil


@dataclass
class Settings:
    root: Path
    state: Path
    workspaces: Path
    terraform: str

    @classmethod
    def load(cls):
        root = Path(os.environ.get("TFPREP_ROOT", Path(__file__).resolve().parents[2])).resolve()
        local_tf = root / ".tools" / "terraform"
        return cls(
            root,
            Path(os.environ.get("TFPREP_STATE", root / ".state")).resolve(),
            Path(os.environ.get("TFPREP_WORKSPACES", root / "workspaces")).resolve(),
            os.environ.get("TFPREP_TERRAFORM", str(local_tf) if local_tf.exists() else shutil.which("terraform") or "terraform"),
        )

