import json
from pathlib import Path
import yaml
from .models import Question, Validator, LessonMetadata, ChallengeContract


class Content:
    def __init__(self, root: Path):
        self.root = root

    def directory(self, domain_id):
        if domain_id not in {f"{n:02}" for n in range(1, 9)}:
            raise ValueError("Unknown course domain")
        return self.root / "curriculum" / f"domain-{domain_id}"

    def domain(self, domain_id):
        directory = self.directory(domain_id)
        metadata = LessonMetadata.model_validate_json((directory/'domain.json').read_text()).model_dump(exclude_none=True)
        challenge=ChallengeContract.model_validate_json((directory/'challenge.json').read_text())
        if challenge.domain_id!=domain_id or challenge.lab_id!=metadata['lab_id']:
            raise ValueError('Challenge metadata does not match the lesson')
        for checkpoint in metadata["checkpoints"]:
            for key in ("correct", "rationale"):
                checkpoint.pop(key, None)
        metadata["challenge"] = (directory / "challenge.md").read_text()
        return metadata

    def domains(self):
        return [self.domain(f"{n:02}") for n in range(1, 9) if (self.directory(f"{n:02}") / "domain.json").exists()]

    def validator(self, domain_id):
        return Validator.model_validate(yaml.safe_load((self.directory(domain_id) / "validator.yaml").read_text()))

    def checkpoints(self, domain_id):
        raw = json.loads((self.directory(domain_id) / "domain.json").read_text())
        return {q["id"]: Question.model_validate(q) for q in raw["checkpoints"]}

    def questions(self):
        path = self.root / "exam-bank" / "questions_004.json"
        return {q["id"]: Question.model_validate(q) for q in json.loads(path.read_text())}

