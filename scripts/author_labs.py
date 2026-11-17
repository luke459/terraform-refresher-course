"""Build the editable/reference HCL trees from reviewed, domain-specific sources."""
from pathlib import Path
import shutil
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
CURRICULUM = ROOT / "curriculum"
COMMON = CURRICULUM / "domain-01/solution"


def write(domain, solution, starter_changes=None, random=False):
    directory = CURRICULUM / f"domain-{domain:02}"
    for variant in ("solution", "starter"):
        dest = directory / variant
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("variables.tf", "versions.tf", "providers.tf", ".terraform.lock.hcl"):
            if name == '.terraform.lock.hcl' and (dest/name).exists():
                continue
            text = (COMMON / name).read_text().replace('Lab       = "01"', f'Lab       = "{domain:02}"')
            if domain == 2 and name == "versions.tf":
                text = text.replace('version = "= 5.92.0"', 'version = "~> 5.80"')
            if domain == 2 and name == 'variables.tf':
                text = text.replace('variable "region" {','# tflint-ignore: terraform_unused_declarations\nvariable "region" {')
            if random and name == "versions.tf":
                text = text.replace('  required_providers {', '  required_providers {\n    random = {\n      source = "hashicorp/random"\n      version = "= 3.7.2"\n    }')
            (dest/name).write_text(text)
        for name,text in solution.items():
            target=dest/name
            target.parent.mkdir(exist_ok=True,parents=True)
            if variant=="starter" and starter_changes and name in starter_changes:
                text=starter_changes[name]
            target.write_text(text.strip()+"\n")


def contract(domain,title,minutes,checks):
    directory=CURRICULUM/f"domain-{domain:02}"
    data={"schema_version":1,"domain_id":f"{domain:02}","title":title,"estimated_minutes":minutes,
          "checks":checks,"teardown_check":"state_and_owned_inventory"}
    (directory/'validator.yaml').write_text(yaml.safe_dump(data,sort_keys=False))


def hcl(id,description,assertions):
    return {"id":id,"type":"hcl_ast","description":description,"assertions":assertions}


def receipt(operation,description=None,**kwargs):
    return {"id":operation.replace('-','_'),"type":"command_receipt","operation":operation,
            "description":description or operation.replace('-',' ').capitalize(),**kwargs}


OWNERSHIP={"id":"ownership","type":"inventory","description":"Cloud resources belong to this attempt"}
NO_CHANGES=receipt('plan-no-changes','A fresh post-apply plan has no changes')


def main():
    providers2=re.sub(r'region\s*=\s*var\.region', 'region = "us-east-1"', (COMMON/'providers.tf').read_text(), count=1).replace('Lab       = "01"','Lab       = "02"')+'''
provider "aws" {
  alias  = "uk"
  region = "eu-west-2"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      Project = "tf-004-prep"
      ManagedBy = "terraform"
      Learner = "local"
      Lab = "02"
      Attempt = var.attempt_id
      RegionRole = "uk"
    }
  }
}
'''
    main2='''
resource "aws_ssm_parameter" "us" {
  name = "/tf004/${var.attempt_id}/region"
  type = "String"
  value = "us-east-1"
}
resource "aws_ssm_parameter" "uk" {
  provider = aws.uk
  name = "/tf004/${var.attempt_id}/region"
  type = "String"
  value = "eu-west-2"
}
output "parameter_name" { value = aws_ssm_parameter.us.name }
'''
    write(2,{'providers.tf':providers2,'main.tf':main2},{'main.tf':main2.replace('provider = aws.uk','provider = aws').replace('value = "eu-west-2"','value = "wrong-region"')})
    contract(2,'Multiple provider configurations',35,[
        hcl('alias_binding','The UK parameter selects aws.uk',[{'path':'resource.aws_ssm_parameter.uk.provider','contains':'aws.uk'}]),
        {'id':'us_parameter','type':'aws_cli','description':'US parameter has its regional value','service':'ssm','operation':'get_parameter','region':'us-east-1','parameters':{'Name':'${outputs.parameter_name}'},'assertions':[{'path':'Parameter.Value','equals':'us-east-1'}]},
        {'id':'uk_parameter','type':'aws_cli','description':'UK parameter has its regional value','service':'ssm','operation':'get_parameter','region':'eu-west-2','parameters':{'Name':'${outputs.parameter_name}'},'assertions':[{'path':'Parameter.Value','equals':'eu-west-2'}]},
        receipt('provider-lock','Checksums were generated for the three supported platforms'),NO_CHANGES,OWNERSHIP])

    main3='''
resource "aws_vpc" "course" { cidr_block = "10.43.0.0/16" }
resource "aws_subnet" "app" {
  vpc_id = aws_vpc.course.id
  cidr_block = "10.43.1.0/24"
}
resource "aws_security_group" "app" {
  name_prefix = "tf004-${var.attempt_id}-app-"
  description = "Disposable course security group"
  vpc_id = aws_vpc.course.id
  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["10.43.0.0/16"]
  }
  lifecycle { create_before_destroy = true }
}
output "security_group_id" { value = aws_security_group.app.id }
'''
    write(3,{'main.tf':main3},{'main.tf':main3.replace('cidr_block = "10.43.1.0/24"','cidr_block="not-a-cidr"')})
    contract(3,'Safe workflow and replacement',40,[receipt('fmt-check'),receipt('apply'),receipt('replace'),receipt('baseline-replaced'),NO_CHANGES,OWNERSHIP])

    main4='''
variable "services" {
  type = map(object({ port = number, cidr = string }))
  default = {
    web = { port = 443, cidr = "10.44.0.0/16" }
    ssh = { port = 22, cidr = "10.44.1.0/24" }
  }
  validation {
    condition = alltrue([for service in values(var.services) : service.port >= 1 && service.port <= 65535 && can(cidrhost(service.cidr, 0))])
    error_message = "Each service needs a valid CIDR and port in 1..65535."
  }
}
variable "secret_version" {
  type = number
  default = 1
}
resource "aws_vpc" "course" { cidr_block = "10.44.0.0/16" }
resource "aws_security_group" "service" {
  for_each = var.services
  name_prefix = "tf004-${var.attempt_id}-${each.key}-"
  description = "Disposable service contract example"
  vpc_id = aws_vpc.course.id
  ingress {
    from_port = each.value.port
    to_port = each.value.port
    protocol = "tcp"
    cidr_blocks = [each.value.cidr]
  }
  lifecycle {
    precondition {
      condition = each.value.port != 22 || each.value.cidr != "0.0.0.0/0"
      error_message = "SSH must not be open to the entire internet."
    }
    postcondition {
      condition = self.vpc_id == aws_vpc.course.id
      error_message = "The security group must belong to the lab VPC."
    }
  }
}
check "service_count" {
  data "aws_security_groups" "course" {
    filter {
      name = "tag:Attempt"
      values = [var.attempt_id]
    }
    filter {
      name = "vpc-id"
      values = [aws_vpc.course.id]
    }
    depends_on = [aws_security_group.service]
  }
  assert {
    condition = length(data.aws_security_groups.course.ids) == length(var.services)
    error_message = "AWS must contain one security group per service."
  }
}
ephemeral "random_password" "password" {
  length = 24
  special = true
}
resource "aws_secretsmanager_secret" "password" {
  name = "tf004-${var.attempt_id}-password"
  recovery_window_in_days = 0
}
resource "aws_secretsmanager_secret_version" "password" {
  secret_id = aws_secretsmanager_secret.password.id
  secret_string_wo = ephemeral.random_password.password.result
  secret_string_wo_version = var.secret_version
}
output "secret_arn" { value = aws_secretsmanager_secret.password.arn }
'''
    bad4=main4.replace('cidr = "10.44.1.0/24"','cidr = "0.0.0.0/0"')
    write(4,{'main.tf':main4},{'main.tf':bad4},random=True)
    contract(4,'Contracts and ephemeral secrets',50,[
        hcl('custom_conditions','Input validation, precondition, postcondition and check are declared',[
            {'path':'variable.services.validation','min_count':1},
            {'path':'resource.aws_security_group.*.for_each','contains':'var.services'},
            {'path':'resource.aws_security_group.*.lifecycle.precondition','min_count':1},
            {'path':'resource.aws_security_group.*.lifecycle.postcondition','min_count':1},
            {'path':'check','min_count':1},
            {'path':'ephemeral.random_password.*','min_count':1},
            {'path':'resource.aws_secretsmanager_secret_version.*.secret_string_wo','contains':'ephemeral.random_password'},
            {'path':'resource.random_password','absent':True}]),
        {'id':'check_assertions','type':'tf_state_json','description':'Top-level check assertions completed successfully','assertions':[{'path':"checks[?address.kind=='check']",'min_count':1},{'path':"checks[?status!='pass']",'absent':True}]},
        {'id':'zero_secret_leak','type':'artifact_leak','description':'The live password is absent from retained Terraform artifacts'},
        receipt('plan-no-managed-changes','The post-apply plan has zero managed-resource/output changes; scoped check reads may remain'),OWNERSHIP])

    main5='''
variable "environments" {
  type = map(object({ cidr = string, subnet_cidr = string }))
  default = {
    dev = { cidr = "10.50.0.0/16", subnet_cidr = "10.50.1.0/24" }
    stage = { cidr = "10.51.0.0/16", subnet_cidr = "10.51.1.0/24" }
  }
}
module "app_tier" {
  source = "./modules/app-tier"
  for_each = var.environments
  network = each.value
  environment = each.key
  attempt_id = var.attempt_id
}
resource "aws_ssm_parameter" "summary" {
  name = "/tf004/${var.attempt_id}/network-summary"
  type = "String"
  value = jsonencode({for name, tier in module.app_tier : name => tier.vpc_id})
}
output "summary_name" { value = aws_ssm_parameter.summary.name }
'''
    child5='''
terraform {
  required_version = "= 1.12.2"
  required_providers { aws = { source = "hashicorp/aws", version = "= 5.92.0" } }
}
variable "network" { type = object({cidr = string, subnet_cidr = string}) }
variable "environment" { type = string }
variable "attempt_id" { type = string }
resource "aws_vpc" "app" {
  cidr_block = var.network.cidr
  tags = { Environment = var.environment }
}
resource "aws_subnet" "app" {
  vpc_id = aws_vpc.app.id
  cidr_block = var.network.subnet_cidr
  tags = { Environment = var.environment }
}
resource "aws_security_group" "app" {
  name_prefix = "tf004-${var.attempt_id}-${var.environment}-"
  description = "Disposable module lab security group"
  vpc_id = aws_vpc.app.id
  tags = { Environment = var.environment }
}
output "vpc_id" { value = aws_vpc.app.id }
output "subnet_id" { value = aws_subnet.app.id }
'''
    write(5,{'main.tf':main5,'modules/app-tier/main.tf':child5},{'main.tf':main5.replace('name => tier.vpc_id','name => tier.aws_vpc.app.id')})
    contract(5,'Reusable module composition',40,[
        hcl('module_instances','Module instances use for_each with explicit inputs',[{'path':'module.app_tier.for_each','contains':'var.environments'},{'path':'module.app_tier.network','contains':'each.value'}]),
        {'id':'module_addresses','type':'tf_state_json','description':'Both dev and stage module instances are present','assertions':[{'path':"values.root_module.child_modules[?address=='module.app_tier[\"dev\"]']",'min_count':1},{'path':"values.root_module.child_modules[?address=='module.app_tier[\"stage\"]']",'min_count':1}]},
        {'id':'module_summary','type':'inventory','operation':'module-summary','description':'Live SSM summary matches the actual dev/stage VPC IDs'},NO_CHANGES,OWNERSHIP])

    main6='''
resource "aws_ssm_parameter" "metadata" {
  name = "/tf004/${var.attempt_id}/drift"
  type = "String"
  value = "desired"
  tags = { Stage = "desired" }
}
moved {
  from = aws_ssm_parameter.legacy
  to = aws_ssm_parameter.metadata
}
removed {
  from = aws_ssm_parameter.detached
  lifecycle { destroy = false }
}
output "parameter_name" { value = aws_ssm_parameter.metadata.name }
'''
    starter6='''
resource "aws_ssm_parameter" "legacy" {
  name = "/tf004/${var.attempt_id}/drift"
  type = "String"
  value = "desired"
  tags = { Stage = "desired" }
}
resource "aws_ssm_parameter" "detached" {
  name = "/tf004/${var.attempt_id}/detached"
  type = "String"
  value = "Remove from state without deleting, then clean up explicitly."
}
output "parameter_name" { value = aws_ssm_parameter.legacy.name }
'''
    write(6,{'main.tf':main6},{'main.tf':starter6})
    bootstrap=CURRICULUM/'domain-06/bootstrap'
    bootstrap.mkdir(parents=True,exist_ok=True)
    for name in ('variables.tf','versions.tf','providers.tf','.terraform.lock.hcl'):
        shutil.copyfile(CURRICULUM/'domain-06/solution'/name,bootstrap/name)
    (bootstrap/'main.tf').write_text('''
resource "aws_s3_bucket" "state" {
  bucket = "tf004-${var.account_id}-${var.attempt_id}-state"
  force_destroy = true
}
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
output "bucket_name" { value = aws_s3_bucket.state.id }
''')
    for variant in ('starter','solution'):
        shutil.copytree(bootstrap,CURRICULUM/f'domain-06/{variant}/bootstrap',dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.terraform','*.tfstate*','tfplan*','tf-debug.log'))
    contract(6,'Native S3 state locking and refactoring',55,[
        hcl('declarative_refactoring','Moved and removed blocks declare the state refactor',[{'path':'moved','min_count':1},{'path':'removed','min_count':1},{'path':'terraform.backend.s3.use_lockfile','equals':True}]),
        receipt('moved-id','The renamed parameter preserves its original AWS identity'),
        receipt('removed-retained','The removed parameter remains live for explicit owned cleanup'),
        receipt('reconcile-locks','Native S3 lock contention and release were verified'),
        {'id':'drift_reconciled','type':'aws_cli','description':'SSM has the desired value after drift reconciliation','service':'ssm','operation':'get_parameter','parameters':{'Name':'${outputs.parameter_name}'},'assertions':[{'path':'Parameter.Value','equals':'desired'}]},
        NO_CHANGES,OWNERSHIP])

    imports7='''
import {
  to = aws_s3_bucket.imported
  id = "tf004-${var.account_id}-${var.attempt_id}-import"
}
import {
  to = aws_iam_policy.imported
  id = "arn:aws:iam::${var.account_id}:policy/tf004-${var.attempt_id}-import"
}
'''
    main7='''
resource "aws_s3_bucket" "imported" {
  bucket = "tf004-${var.account_id}-${var.attempt_id}-import"
  force_destroy = true
}
resource "aws_iam_policy" "imported" {
  name = "tf004-${var.attempt_id}-import"
  description = "Disposable Terraform import exercise"
  policy = jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow", Action = ["s3:GetBucketLocation"], Resource = "arn:aws:s3:::tf004-${var.account_id}-${var.attempt_id}-import"}]})
}
output "bucket_name" { value = aws_s3_bucket.imported.id }
output "policy_arn" { value = aws_iam_policy.imported.arn }
'''
    write(7,{'imports.tf':imports7,'main.tf':main7},{'main.tf':'# Generate resource blocks with the Generate config operation, then refine them.\n'})
    contract(7,'Declarative import without replacement',45,[
        hcl('declarative_import','Both existing objects use import blocks',[{'path':'import','min_count':2}]),
        receipt('baseline-unchanged','Imported resources preserve their setup identifiers'),
        receipt('generate-config','Generated configuration was captured before refinement'),
        receipt('provider-debug','Private provider debugging evidence exists'),NO_CHANGES,OWNERSHIP])

    main8='''
resource "aws_sns_topic" "course" { name = "tf004-${var.attempt_id}-hcp" }
output "topic_arn" { value = aws_sns_topic.course.arn }
'''
    write(8,{'main.tf':main8},{'main.tf':main8.replace('tf004-${var.attempt_id}-hcp','tf004-${var.attempt_id}-incorrect')})
    contract(8,'HCP concepts and local SNS workflow',35,[
        hcl('local_workflow','Use the selected local AWS connection without an HCP dependency',[{'path':'terraform.cloud','absent':True},{'path':'resource.aws_sns_topic.course.name','contains':'-hcp'}]),
        {'id':'sns_topic','type':'aws_cli','description':'AWS confirms the local course topic exists','service':'sns','operation':'get_topic_attributes','parameters':{'TopicArn':'${outputs.topic_arn}'},'assertions':[{'path':'Attributes.TopicArn','contains':':sns:'}]},
        NO_CHANGES,OWNERSHIP])



if __name__=='__main__':
    main()
