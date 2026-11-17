"""Regenerate JSON Schema contracts from the runner's actual validation models."""
from pathlib import Path
import json
from runner.api.models import Validator,Question,CheckResult,LessonMetadata,ChallengeContract

root=Path(__file__).resolve().parents[1]
for name,model in [('validator',Validator),('question',Question),('result',CheckResult),('lesson',LessonMetadata),('challenge',ChallengeContract)]:
    (root/f'schemas/{name}.schema.json').write_text(json.dumps(model.model_json_schema(),indent=2)+'\n')
