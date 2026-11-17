"""Install pinned, checksum-verified Linux runtime tools inside the course image."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, expected):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent":"tfprep-toolchain/0.1"})
            data = urllib.request.urlopen(request, timeout=120).read()
            break
        except OSError:
            if attempt == 2:
                raise
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit("Toolchain archive failed SHA-256 verification")
    return data


def main():
    manifest = json.loads((ROOT / "docker/toolchain.json").read_text())
    arch = {"x86_64":"amd64", "aarch64":"arm64"}[platform.machine()]
    target = "linux_" + arch
    directory = Path("/usr/local/bin")
    for tool in ("terraform", "tflint"):
        version = manifest[tool]["version"]
        name = f"{tool}_{version}_{target}.zip" if tool == "terraform" else f"tflint_{target}.zip"
        url = f"https://releases.hashicorp.com/terraform/{version}/{name}" if tool == "terraform" else f"https://github.com/terraform-linters/tflint/releases/download/v{version}/{name}"
        payload = fetch(url, manifest[tool]["sha256"][target])
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            (directory/tool).write_bytes(archive.read(tool))
        (directory/tool).chmod(0o755)
    version = manifest["awscli"]["version"]
    aws_arch = {"amd64":"x86_64", "arm64":"aarch64"}[arch]
    payload = fetch(f"https://awscli.amazonaws.com/awscli-exe-linux-{aws_arch}-{version}.zip", manifest["awscli"]["sha256"][target])
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            archive.extractall(temp)
            for info in archive.infolist():
                mode = (info.external_attr >> 16) & 0o777
                if mode:
                    (Path(temp)/info.filename).chmod(mode)
        subprocess.run([str(Path(temp)/"aws/install"), "--bin-dir", str(directory)], check=True)
    print(f"Installed verified runtime for {target}")


if __name__ == "__main__":
    main()
