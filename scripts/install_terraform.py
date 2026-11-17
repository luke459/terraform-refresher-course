"""Install the exam runtime locally without changing the host's tfenv settings."""
import hashlib
import io
import platform
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.12.2"
CHECKSUMS = {
    "darwin_arm64": "1ca02f336ff4f993d6441806d38a0bcc0bbca0e3c877b84c9c2dc80cfcd0dc8b",
    "darwin_amd64": "c65aa74bed1dbb1c48ba4bbab11f08e7f7eeb54a422146561490275340468f19",
    "linux_amd64": "1eaed12ca41fcfe094da3d76a7e9aa0639ad3409c43be0103ee9f5a1ff4b7437",
    "linux_arm64": "f8a0347dc5e68e6d60a9fa2db361762e7943ed084a773f28a981d988ceb6fdc9",
}


def main():
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}[platform.machine()]
    target = f"{platform.system().lower()}_{arch}"
    url = f"https://releases.hashicorp.com/terraform/{VERSION}/terraform_{VERSION}_{target}.zip"
    payload = urllib.request.urlopen(url, timeout=90).read()
    if hashlib.sha256(payload).hexdigest() != CHECKSUMS[target]:
        raise SystemExit("Terraform checksum mismatch")
    destination = ROOT / ".tools" / "terraform"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        destination.write_bytes(archive.read("terraform"))
    destination.chmod(0o755)
    print(f"Installed verified Terraform {VERSION} for {target} at {destination}")


if __name__ == "__main__":
    main()
