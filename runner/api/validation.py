import json
from pathlib import Path
import subprocess
import time
import jmespath
from botocore.exceptions import BotoCoreError, ClientError
from .credentials import ConnectionRequired
from .models import CheckResult
from .terraform import config_hash, parsed_hcl, select_nodes, state_resources, terraform_json


AWS_READS = {
    ("s3", "get_bucket_versioning"), ("s3", "get_bucket_encryption"),
    ("ssm", "get_parameter"), ("ec2", "describe_security_groups"),
    ("secretsmanager", "describe_secret"), ("sns", "get_topic_attributes"),
}


class LabValidator:
    def __init__(self, settings, db, content, credentials, inventory):
        self.settings, self.db, self.content, self.credentials, self.inventory = settings, db, content, credentials, inventory

    def state(self, directory, env):
        # Pulling first prevents a missing local state from masquerading as a valid empty state.
        pulled = terraform_json(self.settings, directory, ["state", "pull"], env)
        if pulled.get("version") != 4 or not pulled.get("lineage"):
            raise ValueError("State is missing or is not a valid Terraform state snapshot")
        return terraform_json(self.settings, directory, ["show", "-json"], env)

    def validate(self, attempt, directory, env):
        contract = self.content.validator(attempt["domain_id"])
        context, checks = {}, []
        for check in contract.checks:
            try:
                evidence = self.run_check(check, attempt, directory, env, context)
                result = CheckResult(id=check.id, status="pass", message=check.description, evidence=evidence)
            except ConnectionRequired as exc:
                result = CheckResult(id=check.id, status="blocked", message=str(exc))
            except (ClientError, BotoCoreError) as exc:
                code = exc.response.get("Error", {}).get("Code", "AWS error") if isinstance(exc, ClientError) else "credential/network error"
                result = CheckResult(id=check.id, status="error", message=f"Live AWS check could not complete ({code})")
            except (ValueError, FileNotFoundError) as exc:
                result = CheckResult(id=check.id, status="fail", message=str(exc))
            except Exception as exc:
                result = CheckResult(id=check.id, status="error", message=f"Check could not complete ({type(exc).__name__})")
            checks.append(result.model_dump())
        passed = bool(checks) and all(c["status"] == "pass" for c in checks)
        current_hash = config_hash(directory)
        self.db.execute("UPDATE attempts SET status=?,verified_hash=?,results=? WHERE id=?",
            ("apply_verified" if passed else "active", current_hash if passed else None, json.dumps(checks), attempt["id"]))
        return {"checks": checks, "apply_verified": passed, "percentage": 50 if passed else 0}

    def run_check(self, check, attempt, directory, env, context):
        if check.type == "hcl_ast":
            if "hcl" not in context:
                context["hcl"] = parsed_hcl(directory)
            for assertion in check.assertions:
                nodes = select_nodes(context["hcl"], assertion.path)
                if assertion.min_count is not None and len(nodes) < assertion.min_count:
                    raise ValueError(f"Required HCL structure missing: {assertion.path}")
                if assertion.absent and nodes:
                    raise ValueError(f"HCL structure must be absent: {assertion.path}")
                if assertion.contains and not any(assertion.contains in str(node) for node in nodes):
                    raise ValueError(f"HCL expression does not meet the rule: {assertion.path}")
                if assertion.equals is not None and (not nodes or any(node != assertion.equals for node in nodes)):
                    raise ValueError(f"HCL attribute has an unexpected value: {assertion.path}")
            return {"assertions": len(check.assertions)}
        if check.type in {"tf_state_json", "inventory", "aws_cli", "artifact_leak"}:
            if "state" not in context:
                context["state"] = self.state(directory, env)
            if not state_resources(context["state"]):
                raise ValueError("No deployed resources were found in this attempt's state")
        if check.type == "tf_state_json":
            self.json_assertions(context["state"], check.assertions)
            return {"assertions": len(check.assertions)}
        if check.type == "tf_plan_json":
            plan = terraform_json(self.settings, directory, ["show", "-json", "tfplan"], env)
            if not plan.get("format_version"):
                raise ValueError("A saved plan is required")
            self.json_assertions(plan, check.assertions)
            return {"assertions": len(check.assertions)}
        if check.type == "inventory":
            self.inventory.capture(attempt, context["state"])
            from .resources import PRIMARY
            expected = {r['values']['id'] for r in state_resources(context['state']) if r.get('mode')=='managed' and r['type'] in PRIMARY}
            evidence = self.inventory.verify_owned(attempt, expected)
            if check.operation == 'module-summary':
                vpcs = {r['address'].split('["')[1].split('"]')[0]:r['values']['id'] for r in state_resources(context['state']) if r['type']=='aws_vpc' and r['address'].startswith('module.app_tier[')}
                output = context['state']['values']['outputs']['summary_name']['value']
                value = self.credentials.client('ssm',attempt['region']).get_parameter(Name=output)['Parameter']['Value']
                if json.loads(value) != vpcs or set(vpcs) != {'dev','stage'}:
                    raise ValueError('The live SSM summary must map dev and stage to their actual module VPC IDs')
                evidence['module_summary_matches']=True
            return evidence
        if check.type == "aws_cli":
            if (check.service, check.operation) not in AWS_READS:
                raise ValueError("Validator AWS operation is not allowlisted")
            outputs = {key: value["value"] for key, value in context["state"].get("values", {}).get("outputs", {}).items()}
            params = self.resolve_parameters(check.parameters, outputs)
            client = self.credentials.client(check.service, check.region or attempt["region"])
            response = getattr(client, check.operation)(**params)
            self.json_assertions(response, check.assertions)
            return {"service": check.service, "operation": check.operation, "assertions": len(check.assertions)}
        if check.type == "command_receipt":
            return self.receipt(check, attempt, directory)
        if check.type == "artifact_leak":
            return self.secret_check(attempt, directory, env, context["state"])
        raise ValueError("Unsupported validator check")

    @staticmethod
    def resolve_parameters(value, outputs):
        if isinstance(value, dict):
            return {key: LabValidator.resolve_parameters(item, outputs) for key, item in value.items()}
        if isinstance(value, list):
            return [LabValidator.resolve_parameters(item, outputs) for item in value]
        if isinstance(value, str) and value.startswith("${outputs.") and value.endswith("}"):
            name = value[10:-1]
            if name not in outputs:
                raise ValueError(f"Required output missing: {name}")
            return outputs[name]
        return value

    @staticmethod
    def json_assertions(document, assertions):
        for assertion in assertions:
            value = jmespath.search(assertion.path, document) if assertion.path else document
            if assertion.absent:
                if value not in (None, [], {}):
                    raise ValueError(f"Unexpected value present at {assertion.path}")
            elif assertion.min_count is not None:
                if not isinstance(value, (list, dict, str)) or len(value) < assertion.min_count:
                    raise ValueError(f"Not enough values at {assertion.path}")
            elif assertion.contains is not None:
                if assertion.contains not in str(value):
                    raise ValueError(f"Expected content missing at {assertion.path}")
            elif value != assertion.equals:
                raise ValueError(f"Unexpected value at {assertion.path}")

    def receipt(self, check, attempt, directory):
        operation = check.operation or "apply"
        if operation == "plan-no-changes":
            row = self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation='plan' AND status='succeeded' ORDER BY created DESC LIMIT 1", (attempt["id"],))
            applied = self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation='apply' AND status='succeeded' ORDER BY created DESC LIMIT 1", (attempt["id"],))
            if not row or not applied or row["created"] <= applied["created"] or row["exit_code"] != 0:
                raise ValueError("Run a fresh plan after apply and reach detailed exit code 0")
            params = json.loads(row['params'])
            if 'terminal_args' in params and not params.get('detailed_exitcode'):
                raise ValueError('Run terraform plan -detailed-exitcode after apply so exit code 0 proves there are no changes.')
        elif operation == 'plan-no-managed-changes':
            row=self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation='plan' AND status='succeeded' ORDER BY created DESC LIMIT 1",(attempt['id'],))
            applied=self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation='apply' AND status='succeeded' ORDER BY created DESC LIMIT 1",(attempt['id'],))
            if not row or not applied or row['created']<=applied['created'] or row['config_hash']!=config_hash(directory):
                raise ValueError('Run a fresh post-apply plan for this configuration')
            import hashlib
            if hashlib.sha256((directory/'tfplan').read_bytes()).hexdigest()!=row['plan_hash']:
                raise ValueError('The saved plan no longer matches its execution receipt')
            plan=terraform_json(self.settings,directory,['show','-json','tfplan'],self.credentials.environment(attempt['account']))
            managed=[r for r in plan.get('resource_changes',[]) if r.get('mode')=='managed' and r.get('change',{}).get('actions')!=['no-op']]
            outputs=[value for value in plan.get('output_changes',{}).values() if value.get('actions')!=['no-op']]
            if managed or outputs:
                raise ValueError('Managed resources or root outputs still have proposed changes')
            reads=sum(r.get('mode')=='data' and r.get('change',{}).get('actions')==['read'] for r in plan.get('resource_changes',[]))
            return {'job_id':row['id'],'exit_code':row['exit_code'],'managed_changes':0,'output_changes':0,'data_reads':reads}
        elif operation == "replace":
            rows = self.db.all("SELECT * FROM jobs WHERE attempt_id=? AND operation='plan' AND status='succeeded' ORDER BY created DESC", (attempt["id"],))
            row = next((r for r in rows if json.loads(r["params"]).get("replace")), None)
            applied = self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation='apply' AND status='succeeded' ORDER BY created DESC LIMIT 1", (attempt["id"],))
            if not row or not applied or row["created"] >= applied["created"]:
                raise ValueError("Create and apply a plan using the replacement option")
        elif operation == "baseline-unchanged":
            baseline = json.loads(attempt["baseline"])
            if not baseline:
                raise ValueError("Capture the resource baseline before refactoring")
            current = {r["address"]: r["values"].get("id") for r in state_resources(self.state(directory, self.credentials.environment(attempt["account"]))) if r.get("mode") == "managed"}
            if not set(baseline.values()) <= set(current.values()):
                raise ValueError("A previously captured resource ID was replaced or lost")
            return {"preserved_ids": len(baseline)}
        elif operation == "baseline-replaced":
            baseline = json.loads(attempt["baseline"])
            previous = baseline.get("aws_security_group.app")
            current = next((r["values"].get("id") for r in state_resources(self.state(directory, self.credentials.environment(attempt["account"]))) if r["address"] == "aws_security_group.app"), None)
            if not previous or not current or previous == current:
                raise ValueError("Capture the initial security group ID, then replace that group")
            return {"replacement_confirmed": True}
        elif operation == "fmt-check":
            run = subprocess.run([self.settings.terraform, "fmt", "-check", "-recursive"], cwd=directory, capture_output=True, timeout=30)
            if run.returncode:
                raise ValueError("Terraform formatting check failed")
            return {"formatted": True}
        elif operation == "moved-id":
            before = json.loads(attempt['baseline']).get('aws_ssm_parameter.legacy')
            state = self.state(directory, self.credentials.environment(attempt['account']))
            after = next((r['values'].get('id') for r in state_resources(state) if r['address']=='aws_ssm_parameter.metadata'),None)
            if not before or before != after:
                raise ValueError('Capture the legacy parameter ID before refactoring; the renamed resource must preserve it')
            return {'moved_id_preserved':True}
        elif operation == "provider-debug":
            path = directory/'tf-debug.log'
            if not path.is_file() or 'provider.terraform-provider-aws' not in path.read_text(errors='replace'):
                raise ValueError('Run a provider operation with debug capture enabled')
            return {'provider_debug_captured':True}
        elif operation == 'removed-retained':
            rows = self.inventory.rows(attempt['id'])
            detached = next((r for r in rows if r['address']=='aws_ssm_parameter.detached'),None)
            state=self.state(directory,self.credentials.environment(attempt['account']))
            if not detached or any(r['address']=='aws_ssm_parameter.detached' for r in state_resources(state)) or not self.inventory.inspect(detached)['exists']:
                raise ValueError('The inventoried detached parameter must remain live outside Terraform state before explicit cleanup')
            return {'removed_object_retained':True}
        elif operation == 'generate-config':
            rows = self.db.all("SELECT * FROM jobs WHERE attempt_id=? AND operation='generate-config' AND result IS NOT NULL ORDER BY created DESC",(attempt['id'],))
            row = next((r for r in rows if json.loads(r['result']).get('generated_config')),None)
            if not row:
                raise ValueError('Generate configuration through the course operation before refining it')
            return {'job_id':row['id'],'generated_config_captured':True}
        else:
            row = self.db.one("SELECT * FROM jobs WHERE attempt_id=? AND operation=? AND status='succeeded' ORDER BY created DESC LIMIT 1", (attempt["id"], operation))
        if not row or (operation != 'generate-config' and row["config_hash"] != config_hash(directory)):
            raise ValueError(f"A successful {operation} receipt for this configuration is required")
        return {"job_id": row["id"], "exit_code": row["exit_code"]}

    def secret_check(self, attempt, directory, env, state):
        resources = state_resources(state)
        secret = next((r for r in resources if r["type"] == "aws_secretsmanager_secret"), None)
        version = next((r for r in resources if r["type"] == "aws_secretsmanager_secret_version"), None)
        if not secret or not version:
            raise ValueError("A real secret and secret version are required")
        if any(r["type"] == "random_password" for r in resources):
            raise ValueError("Use an ephemeral password resource instead of a managed random_password")
        schema = terraform_json(self.settings, directory, ["providers", "schema", "-json"], env)
        attribute = schema["provider_schemas"]["registry.terraform.io/hashicorp/aws"]["resource_schemas"]["aws_secretsmanager_secret_version"]["block"]["attributes"]["secret_string_wo"]
        if not attribute.get("write_only"):
            raise ValueError("The provider does not support the required write-only attribute")
        response = self.credentials.client("secretsmanager", attempt["region"]).get_secret_value(SecretId=secret["values"]["id"])
        value = response.get("SecretString")
        if not value:
            raise ValueError("A nonempty live secret string is required")
        self.credentials.resolved_secrets.add(value)
        plan = terraform_json(self.settings, directory, ["show", "-json", "tfplan"], env)
        def leaves(document):
            if isinstance(document, dict):
                return [s for item in document.values() for s in leaves(item)]
            if isinstance(document, list):
                return [s for item in document for s in leaves(item)]
            return [document] if isinstance(document, str) else []
        if any(value in text for text in leaves(state) + leaves(plan)):
            raise ValueError("The live secret appears in Terraform state or saved-plan JSON")
        inspected = 0
        for path in directory.rglob("*"):
            if not path.is_file() or ".terraform" in path.relative_to(directory).parts:
                continue
            if path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("A workspace artifact exceeds the leak scanner's size limit")
            if value.encode() in path.read_bytes():
                raise ValueError("The live secret appears in a retained workspace artifact")
            inspected += 1
        return {"write_only_verified": True, "artifacts_scanned": inspected, "live_value_compared": True}

    def teardown(self, attempt, directory, env):
        destroyed = self.db.one("SELECT id FROM jobs WHERE attempt_id=? AND operation='destroy' AND status='succeeded' ORDER BY created DESC LIMIT 1", (attempt["id"],))
        if not destroyed:
            return {"complete": False, "message": "Run Terraform destroy successfully before the cleanup check"}
        if not self.inventory.rows(attempt["id"]):
            return {"complete": False, "message": "No owned-resource inventory was captured; cleanup cannot be proven"}
        state = self.state(directory, env)
        managed = [r["address"] for r in state_resources(state) if r.get("mode") == "managed"]
        if managed:
            return {"complete": False, "message": "Managed resources remain in state", "remaining_state": managed}
        self.inventory.reconcile(attempt)
        remaining = self.inventory.absence(attempt)
        if remaining:
            return {"complete": False, "message": "Cloud resources remain or deletion is pending", "remaining_cloud": remaining}
        current=self.db.one('SELECT * FROM attempts WHERE id=?',(attempt['id'],))
        graded=self.db.one("SELECT finished FROM jobs WHERE attempt_id=? AND operation='validate-lab' AND status='succeeded' AND config_hash=? ORDER BY created DESC LIMIT 1",(attempt['id'],current['verified_hash'])) if current['verified_hash'] else None
        destroyed_at=self.db.one("SELECT created FROM jobs WHERE id=?",(destroyed['id'],))['created']
        if not graded or not graded['finished'] or graded['finished']>destroyed_at:
            self.db.execute("UPDATE attempts SET status='cleaned' WHERE id=?",(attempt['id'],))
            return {'complete':False,'cleaned':True,'message':'Owned resources are absent, but apply assertions were never verified for this attempt. Start a new attempt to earn completion.','percentage':0}
        self.db.execute("UPDATE attempts SET status='complete',config_hash=? WHERE id=?", (config_hash(directory), attempt["id"]))
        return {"complete": True, "message": "State is empty and every inventoried cloud resource is absent", "percentage": 100}

