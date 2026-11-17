"""Domain metadata and independent inline checkpoint authoring."""
from author_domains import DOMAINS


def scenario(prompt, choices, correct, explanation):
    return dict(prompt=prompt,choices=choices,correct=correct,explanation=explanation)


def domain(n,title,subtitle,minutes,lab_minutes,objectives,lab_id,before,after,exercises,failures,types):
    return dict(id=f'{n:02}',title=title,subtitle=subtitle,minutes=minutes,lab_minutes=lab_minutes,
        objectives=objectives,lab_id=lab_id,difficulty='Deep dive' if n in [4,6] else 'Catch up',icon='layers',
        delta={'before':before,'after':after},exercises=exercises,expected_starter_failures=failures,
        resource_types=types,cost={'target_usd':0.01,'currency':'USD','regions':['us-east-1','eu-west-2'] if n==2 else ['eu-west-1','us-east-1','eu-west-2'],
        'pricing_date':'2026-11-14','assumptions':'Short-lived resources, no compute, standard parameters, no uploads; gross usage before account credits.','free_tier_guaranteed':False})


DOMAINS.extend([
domain(2,'Terraform fundamentals','Providers, aliases, versions, and the state relationship.',75,35,['2a','2b','2c','2d'],'lab-02-multi-provider',
    'Provider constraints often looked like an installation detail.', 'Treat provider selection and cross-platform checksums as part of reproducibility.',[
    {'id':'constraint-solver','title':'Constraint Solver','description':'Try the difference between a minor-series and patch-series pessimistic constraint.'},
    {'id':'lockfile-inspector','title':'Lockfile Inspector','description':'Diagnose the checksum problem without inventing platform labels in the lockfile.','cases':[
        scenario('A lockfile initialized on macOS must support both Linux container architectures.',['Search for a linux label in each hash','Run providers lock with explicit -platform options','Delete the lockfile every run'],'Run providers lock with explicit -platform options','Generate checksums for linux_amd64, linux_arm64 and darwin_arm64, then test readonly initialization.'),
        scenario('An allowed newer provider exists, but the committed lockfile still selects 5.92.0.',['init always selects the newest version','init respects the compatible locked version','The lockfile only manages modules'],'init respects the compatible locked version','An explicit init -upgrade considers new allowed versions.') ]},
    ],['alias_binding','uk_parameter'],['aws_ssm_parameter']),
domain(3,'Core Terraform workflow','Review plans, apply deliberately, and replace safely.',85,40,['3a','3b','3c','3d','3e','3f','3g'],'lab-03-safe-workflow',
    'You may remember taint and imperative refresh habits.', 'Use saved plans, -replace and -refresh-only with precise exit-code checks.',[
    {'id':'cli-flag-lab','title':'CLI Flag Lab','description':'Choose the command that matches the operational intent.','cases':[
        scenario('Replace only a damaged security group after reviewing a saved plan.',['terraform taint aws_security_group.app','terraform plan -replace=aws_security_group.app -out=tfplan','terraform state rm aws_security_group.app'],'terraform plan -replace=aws_security_group.app -out=tfplan','Apply the reviewed tfplan; replacement is a planned infrastructure action.'),
        scenario('Accept observed remote changes into state without changing infrastructure.',['terraform apply -refresh-only','terraform apply -refresh=false','terraform destroy'],'terraform apply -refresh-only','Refresh-only updates state and outputs, not the desired HCL or cloud objects.'),
        scenario('Check formatting in CI without rewriting files.',['terraform fmt -check -recursive','terraform fmt -recursive','terraform init -upgrade'],'terraform fmt -check -recursive','The -check flag reports differences without formatting the files.') ]}],
    ['fmt_check','configuration_valid'],['aws_vpc','aws_subnet','aws_security_group']),
domain(4,'Terraform configuration','Contracts, iteration, lifecycle, and secrets that stay out of state.',110,50,['4a','4b','4c','4d','4e','4f','4g','4h'],'lab-04-contracts-and-ephemeral',
    'Sensitive output redaction could be mistaken for secret protection.', 'Combine ephemeral values with provider-supported write-only fields and verify real artifacts.',[
    {'id':'evaluation-order','title':'Evaluation Order Visualizer','description':'Trace known values, deferred conditions, blocking failures, and non-blocking checks.'},
    {'id':'state-leak-inspector','title':'State Leak Inspector','description':'Compare redaction with non-persistence using illustrative Terraform state.'}],
    ['ssh_precondition'],['aws_vpc','aws_security_group','aws_secretsmanager_secret','aws_secretsmanager_secret_version']),
domain(5,'Terraform modules','Build clear interfaces and stable module instances.',85,40,['5a','5b','5c','5d'],'lab-05-modular-network',
    'A flat stack may have made every internal attribute feel globally available.', 'Pass typed inputs and publish explicit outputs across module boundaries.',[
    {'id':'scope-debugger','title':'Scope Debugger','description':'Repair the boundary between a root module and a child module.','cases':[
        scenario('The root tries module.app_tier.aws_vpc.app.id. What interface should it use?',['Expose output vpc_id in the child and use module.app_tier.vpc_id','Read the child resource directly','Put the root local in a different file'],'Expose output vpc_id in the child and use module.app_tier.vpc_id','A child publishes values through outputs; its resource namespace is private.'),
        scenario('A child needs a value stored in a root local.',['Use local.root_value from inside the child','Pass it as an input variable','Use an output block inside the child to read the root'],'Pass it as an input variable','Module scope does not implicitly inherit root locals.'),
        scenario('A Git-sourced module must use release v1.2.0.',['Set version in the module block','Add ?ref=v1.2.0 to its Git source','Edit .terraform.lock.hcl'],'Add ?ref=v1.2.0 to its Git source','The version argument is for registry modules; Git uses source ref selection.') ]}],
    ['module_output_reference'],['aws_vpc','aws_subnet','aws_security_group','aws_ssm_parameter']),
domain(6,'Terraform state management','Native S3 locks, drift, and declarative refactoring.',100,55,['6a','6b','6c','6d'],'lab-06-native-s3-locking',
    'S3 locking commonly paired the state bucket with DynamoDB.', 'Use S3 lockfiles, migrate deliberately, and preserve IDs through moved blocks.',[
    {'id':'lock-contention','title':'Lock Contention Lab','description':'Observe acquisition, contention, and release without touching a live state lock.'}],
    ['declarative_refactoring'],['aws_s3_bucket','aws_s3_bucket_versioning','aws_s3_bucket_server_side_encryption_configuration','aws_s3_bucket_public_access_block','aws_ssm_parameter']),
domain(7,'Maintain infrastructure','Import without replacement and debug with useful evidence.',85,45,['7a','7b','7c'],'lab-07-declarative-import',
    'Imports often meant an isolated terraform import command and hand-written HCL.', 'Use import blocks and generated configuration, then review identities and provider logs.',[
    {'id':'log-triage','title':'Log Triage','description':'Isolate an AWS provider permissions failure from a noisy Terraform trace.'}],
    ['missing_import_targets'],['aws_s3_bucket','aws_iam_policy']),
domain(8,'HCP Terraform concepts','Practice collaboration and governance without an HCP account.',80,35,['8a','8b','8c','8d'],'lab-08-hcp-concepts',
    'Terraform Cloud named the hosted platform and its workspaces.', 'Understand HCP projects, workspace workflows and governance using local simulations.',[
    {'id':'governance-sandbox','title':'Governance & Hierarchy Sandbox','description':'A local simulation of projects, variable sets, run triggers and policy behavior. No HCP account is needed.','cases':[
        scenario('Share environment settings with workspaces in one project.',['Use a project-scoped variable set','Put all workspaces in one state file','Copy a local .aws directory into each plan'],'Use a project-scoped variable set','Variable sets share scoped values; each workspace still keeps its own state.'),
        scenario('A pull request should show proposed infrastructure effects without applying.',['Speculative plan','Automatic destroy','A production apply'],'Speculative plan','A speculative plan previews a proposal and cannot be applied as a normal approved run.'),
        scenario('A successful apply should queue a dependent workspace run.',['A run trigger','An input variable default','An AWS provider alias'],'A run trigger','Run triggers connect workspace workflows; they do not merge their state.') ]}],
    ['local_workflow'],['aws_sns_topic']),
])


CHECKPOINTS={
1:[('1a','A script creates a bucket every time it runs. What should the Terraform replacement describe?',[
    ('The bucket and its desired settings','Terraform computes operations from desired configuration and tracked state.'),('The exact API call sequence','The dependency graph determines operation order.')], 'a'),
   ('1b','Which result proves a second detailed-exitcode plan has no changes?',[
    ('Exit 0','With -detailed-exitcode, 0 means success with an empty diff.'),('Exit 2','Exit 2 means proposed changes.')],'a'),
   ('1c','Two AWS regions are necessarily a multi-cloud architecture.',[
    ('True','Regions can belong to the same cloud provider.'),('False','Two provider configurations for AWS are not two different clouds.')],'b')],
2:[('2a','Which constraint allows AWS 5.92.0 but remains below 6.0?',[
    ('~> 5.80','It allows the remainder of the 5.x series from 5.80 onward.'),('~> 5.80.0','This remains below 5.81.0.')],'a'),
   (['2b','2c'],'How does a resource select the UK AWS configuration, and which component makes its AWS API calls?',[
    ('provider = aws.uk; the AWS provider plugin makes the API calls','The meta-argument routes to the alias, and the plugin implements provider API interactions.'),('region = aws.uk; Terraform core replaces the AWS plugin','A resource region argument is not the provider selector, and core does not replace the provider API implementation.')],'a'),
   ('2d','Does state replace the need to keep desired configuration?',[
    ('Yes','State tracks associations and observations; it is not desired configuration.'),('No','Both configuration and state serve distinct purposes.')],'b')],
3:[(['3a','3b','3c','3d'],'A fresh checkout is missing modules/providers. Which sequence prepares and checks it before approving infrastructure changes?',[
    ('Initialize, validate configuration, then generate and review a plan','Init installs dependencies; validation checks consistency; planning exposes the intended changes.'),('Apply immediately, then format and delete state','This skips preparation/review and risks losing management relationships.')],'a'),
   ('3e','Which command applies the exact saved plan named reviewed.plan?',[
    ('terraform apply reviewed.plan','A positional saved-plan path applies that reviewed artifact.'),('terraform apply -out=reviewed.plan','-out is a plan flag, not an apply flag.')],'a'),
   (['3f','3g'],'Which operation removes managed infrastructure, and why does fmt -check not replace it?',[
    ('Destroy removes managed objects; fmt -check only checks source formatting','Formatting does not execute infrastructure deletion.'),('fmt -check deletes resources after rewriting their files','The check flag neither rewrites files nor destroys cloud objects.')],'a')],
4:[(['4c','4h'],'A password input and root output are marked sensitive. Does this remove their value from state?',[
    ('Yes','Sensitive is a redaction mark, not a persistence boundary.'),('No','Use an appropriate ephemeral-to-write-only flow to omit the value.')],'b'),
   (['4a','4b','4f','4g'],'A check data source reads a managed resource through its ID reference. What do that reference and a false check assertion mean?',[
    ('The reference carries a dependency; the data source reads, and a failed check warns','Resources own lifecycle, data sources query, references carry graph edges, and checks are non-blocking assertions.'),('The data source owns deletion; file order controls dependencies and a check always aborts apply','This confuses ownership, graph ordering and check failure behavior.')],'a'),
   (['4d','4e'],'Which design uses unique unordered known service names as stable instance keys?',[
    ('set(string) with for_each over non-sensitive values','A set supplies unique names without positional identity; for_each uses them as keys.'),('A tuple with count, because indices never shift after removing an item','Tuple positions and count indices do not establish stable named identity.')],'a')],
5:[('5b','Can a child directly read a local declared only in the root module?',[
    ('Yes','Module scopes are separate.'),('No','Pass the value through a declared input.')],'b'),
   ('5c','How should the root read a child network ID?',[
    ('Through a child output','Outputs define the child interface.'),('Through the child resource address','Child internals are not exposed as root attributes.')],'a'),
   (['5a','5d'],'How do registry and Git module sources select versions?',[
    ('Registry uses version; Git uses a source ref','The source kind determines the applicable version-selection mechanism.'),('Every source is locked by .terraform.lock.hcl','The provider lockfile does not pin every module package.')],'a')],
6:[(['6a','6b','6c'],'Moving local state to an S3 backend, which settings/workflow provide native locking and carry the snapshot?',[
    ('use_lockfile=true with init -migrate-state and the intended backend configuration','Locking is explicit; migration transfers the local snapshot into the selected remote backend.'),('encrypt=true alone; every workspace state merges automatically','Encryption is not locking, and state boundaries do not merge automatically.')],'a'),
   ('6d','Does refresh-only apply restore a console change to the HCL setting?',[
    ('Yes','It updates observations in state rather than changing the remote setting.'),('No','A normal plan/apply is needed to reconcile the desired setting.')],'b'),
   ('6d','What does removed with destroy=false do to the live resource?',[
    ('Leaves it live while removing Terraform ownership','Track it for explicit cleanup in this course.'),('Deletes it immediately','destroy=false expressly avoids destruction.')],'a')],
7:[('7a','Which identifier does an S3 bucket import require?',[
    ('The bucket name','The AWS provider imports this resource by bucket name.'),('The Terraform resource address alone','The address identifies the configuration target, not the remote object.')],'a'),
   ('7b','Does terraform state rm destroy the cloud object?',[
    ('Yes','It removes the association from state only.'),('No','The cloud object remains and needs deliberate ownership/cleanup handling.')],'b'),
   ('7c','Which setting isolates provider debug logging?',[
    ('TF_LOG_PROVIDER=DEBUG','This selects provider logging separately from core.'),('TF_LOG_PATH=DEBUG','TF_LOG_PATH specifies a destination path.')],'a')],
8:[('8c','What is the relationship between a project and a workspace?',[
    ('A project groups workspaces','Workspaces retain separate configuration/state/run histories.'),('A project is one shared state file','Projects are an organizational grouping, not a single state boundary.')],'a'),
   ('8b','Which pair contains OPA enforcement levels?',[
    ('advisory and mandatory','OPA uses this pair; authorized override behavior depends on permissions/settings.'),('soft-mandatory and hard-mandatory','Those labels belong to Sentinel rather than OPA.')],'a'),
   (['8a','8d'],'A local CLI starts a remote HCP run. Where are provider operations executed?',[
    ('In the remote run environment','CLI-driven describes the trigger; remote describes execution.'),('Always on the CLI machine','A local trigger does not imply local execution.')],'a')],
}
