from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from runner.regions import AWSRegion


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AWSConnection(Contract):
    mode: Literal["profile", "keys"]
    profile: str | None = Field(None, min_length=1, max_length=128)
    access_key_id: SecretStr | None = None
    secret_access_key: SecretStr | None = None
    session_token: SecretStr | None = None
    region: AWSRegion = "us-east-1"

    @model_validator(mode="after")
    def complete_method(self):
        if self.mode == "profile":
            if not self.profile or any([self.access_key_id, self.secret_access_key, self.session_token]):
                raise ValueError("Provide a profile name without access-key fields")
        elif self.profile or not self.access_key_id or not self.secret_access_key:
            raise ValueError("Provide an access key ID and secret without a profile")
        return self


class StartAttempt(Contract):
    domain_id: str = Field(pattern=r"^0[1-8]$")


class RunOperation(Contract):
    operation: Literal["init", "fmt", "validate", "plan", "apply", "destroy", "state-list", "output", "setup-import", "generate-config", "bootstrap-init", "bootstrap-plan", "bootstrap-apply", "bootstrap-destroy", "migrate-remote", "migrate-local", "capture-baseline", "simulate-drift", "reconcile-locks", "provider-lock"]
    replace: str | None = Field(None, pattern=r"^[A-Za-z0-9_.\[\]\"-]+$", max_length=256)
    refresh_only: bool = False
    debug: bool = False


class Assertion(Contract):
    path: str | None = None
    equals: Any = None
    min_count: int | None = Field(None, ge=0)
    contains: str | None = None
    absent: bool = False


class Check(Contract):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    type: Literal["hcl_ast", "tf_state_json", "tf_plan_json", "aws_cli", "artifact_leak", "command_receipt", "inventory"]
    description: str
    assertions: list[Assertion] = []
    service: str | None = None
    operation: str | None = None
    parameters: dict[str, Any] = {}
    region: str | None = None
    resource_address: str | None = None

    @model_validator(mode='after')
    def substantive_check(self):
        if self.type in {'hcl_ast','tf_state_json','tf_plan_json','aws_cli'} and not self.assertions:
            raise ValueError('This check type requires explicit assertions')
        if self.type=='aws_cli' and (not self.service or not self.operation):
            raise ValueError('AWS checks require a service and operation')
        if self.type=='command_receipt' and not self.operation:
            raise ValueError('Command receipts require an operation')
        for assertion in self.assertions:
            if not assertion.path or not (assertion.absent or assertion.equals is not None or assertion.min_count is not None or assertion.contains is not None):
                raise ValueError('Assertions require a path and an explicit predicate')
        return self


class Validator(Contract):
    schema_version: Literal[1] = 1
    domain_id: str = Field(pattern=r"^0[1-8]$")
    title: str
    estimated_minutes: int = Field(gt=0)
    checks: list[Check] = Field(min_length=1)
    teardown_check: Literal["state_and_owned_inventory"] = "state_and_owned_inventory"


class CheckResult(Contract):
    id: str
    status: Literal["pass", "fail", "error", "blocked", "skipped"]
    message: str
    evidence: dict[str, Any] = {}


class Question(Contract):
    id: str
    domain_id: str = Field(pattern=r"^0[1-8]$")
    objectives: list[str] = Field(min_length=1)
    type: Literal["single", "multiple", "boolean"]
    prompt: str
    code: str | None = None
    choices: dict[str, str]
    correct: list[str]
    rationale: dict[str, str]
    difficulty: Literal["recall", "application", "analysis"]
    source_url: str
    terraform_version: Literal["1.12.2"] = "1.12.2"
    reviewed: str = "2026-11-14"

    @model_validator(mode="after")
    def consistent_choices(self):
        if not self.correct or not set(self.correct) <= set(self.choices):
            raise ValueError("Answer must reference available choices")
        if set(self.rationale) != set(self.choices):
            raise ValueError("Each choice requires a rationale")
        if self.type != "multiple" and len(self.correct) != 1:
            raise ValueError("Single/boolean questions need one answer")
        if self.type == "multiple" and len(self.correct) < 2:
            raise ValueError("Multiple-answer questions need at least two answers")
        return self


class CreateExam(Contract):
    mode: Literal["practice", "mock"] = "practice"
    domain_id: str | None = Field(None, pattern=r"^0[1-8]$")
    mock_set: Literal["A", "B"] = "A"
    question_count: int | None = Field(None,ge=1,le=57)


class Answer(Contract):
    question_id: str
    selected: list[str]
    flagged: bool = False


class CostEstimate(Contract):
    target_usd: float = Field(gt=0)
    currency: Literal['USD']
    regions: list[AWSRegion]
    pricing_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    assumptions: str
    free_tier_guaranteed: Literal[False]


class Scenario(Contract):
    prompt: str
    choices: list[str]
    correct: str
    explanation: str


class Exercise(Contract):
    id: str
    title: str
    description: str
    cases: list[Scenario] | None = None


class Delta(Contract):
    before: str
    after: str


class LessonMetadata(Contract):
    id: str = Field(pattern=r'^0[1-8]$')
    title: str
    subtitle: str
    minutes: int = Field(gt=0)
    lab_minutes: int = Field(gt=0)
    objectives: list[str]
    lab_id: str
    difficulty: str
    icon: str
    delta: Delta
    exercises: list[Exercise]
    checkpoints: list[Question] = Field(min_length=3,max_length=3)
    expected_starter_failures: list[str]
    resource_types: list[str]
    cost: CostEstimate


class ChallengeContract(Contract):
    schema_version: Literal[1] = 1
    domain_id: str = Field(pattern=r'^0[1-8]$')
    lab_id: str
    estimated_minutes: int = Field(gt=0)
    prerequisites: list[str]
    resource_types: list[str]
    cost: CostEstimate
    instructions_file: Literal['challenge.md'] = 'challenge.md'
    teardown_gate: Literal['state_and_owned_inventory_and_prior_apply_validation'] = 'state_and_owned_inventory_and_prior_apply_validation'

