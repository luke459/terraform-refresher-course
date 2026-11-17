import hashlib
import json
from pathlib import Path
import subprocess
import hcl2
from hcl2.utils import SerializationOptions


def config_hash(directory: Path):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not any(part in {".terraform", ".git"} for part in path.relative_to(directory).parts):
            if path.suffix in {".tf", ".tfvars", ".hcl"} or path.name.endswith(('.tfvars.json','.tf.json')):
                digest.update(str(path.relative_to(directory)).encode())
                digest.update(path.read_bytes())
    return digest.hexdigest()


def parsed_hcl(directory):
    combined = {}
    for path in sorted([*directory.glob("*.tf"),*directory.glob("*.tf.json")]):
        with path.open() as handle:
            options = SerializationOptions(strip_string_quotes=True, explicit_blocks=False, with_comments=False)
            parsed = json.load(handle) if path.name.endswith('.tf.json') else hcl2.load(handle, serialization_options=options)
            for key, value in parsed.items():
                combined.setdefault(key, []).extend(value if isinstance(value, list) else [value])
    return combined


def select_nodes(value, path):
    tokens = path.split(".") if path else []

    def walk(item, parts):
        if not parts:
            return list(item) if isinstance(item,list) else [item]
        if isinstance(item, list):
            return [found for child in item for found in walk(child, parts)]
        if not isinstance(item, dict):
            return []
        key, rest = parts[0], parts[1:]
        values = item.values() if key == "*" else [item[key]] if key in item else []
        return [found for child in values for found in walk(child, rest)]

    return walk(value, tokens)


def state_resources(state):
    def collect(module):
        return list(module.get("resources", [])) + [r for child in module.get("child_modules", []) for r in collect(child)]
    return collect(state.get("values", {}).get("root_module", {}))


def terraform_json(settings, directory, args, env):
    result = subprocess.run([settings.terraform, *args], cwd=directory, env=env, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ValueError("Terraform could not inspect this workspace. Initialize it and check its backend connection.")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise ValueError("Terraform returned an invalid JSON artifact") from None

