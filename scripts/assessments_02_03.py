"""Original provider and workflow assessment scenarios."""


def author(q):
    q(2,'2a','A team requires AWS 5.80 patch releases without allowing 5.81. Which constraint fits?',[
        ('~> 5.80.0','The third component restricts upgrades to the 5.80 patch series.'),
        ('~> 5.80','This permits later 5.x minor releases.'),
        ('>= 5.80','This has no upper bound and can allow 6.x.'),
        ('!= 5.81','Excluding one version does not establish a patch-series range.')])
    q(2,'2a','The constraint permits newer versions but init selects the committed compatible version. How do you intentionally reconsider that selection?',[
        ('Run terraform init -upgrade and review the resulting lockfile and plan.','The upgrade option considers newer allowed dependencies.'),
        ('Rename the provider alias.','Aliases select configurations, not newer package versions.'),
        ('Delete the infrastructure state.','State deletion is unrelated to a controlled provider upgrade.'),
        ('Run terraform fmt.','Formatting does not change dependency selection.')])
    q(2,'2a','Which TWO items belong in version control for repeatable provider installation? Choose two.',[
        ('The required_providers constraints.','They declare provider sources and allowed versions.'),
        ('.terraform.lock.hcl.','It records selected provider versions and integrity checksums.'),
        ('The .terraform plugin binaries for one developer OS.','Provider installation caches are working-directory artifacts, not the portable source contract.'),
        ('A plaintext AWS credentials file.','Credentials are not part of the dependency contract and must not be committed.')],'ab')
    q(2,'2a','A Linux ARM64 container consumes the same course configuration as an Apple Silicon host. Which packages should portability checks include?',[
        ('linux_arm64 and darwin_arm64, plus linux_amd64 for the other supported container architecture.','Operating system and architecture both matter for provider packages.'),
        ('Only darwin_arm64 because the physical host is a Mac.','The container executes Linux binaries.'),
        ('Only windows_amd64 because ZIP files are portable.','The archive format does not make an executable cross-platform.'),
        ('No package checksums are needed when versions match.','Version pinning does not replace integrity checks.')])
    q(2,'2b','Which responsibility belongs primarily to an AWS provider plugin rather than Terraform core?',[
        ('Translating resource operations into AWS API calls.','The provider implements resource schemas and API interactions.'),
        ('Parsing every Terraform language expression for every provider.','Core handles the language and graph orchestration.'),
        ('Assigning exam questions to learning domains.','That is course application behavior.'),
        ('Making all cloud APIs transactional.','Terraform providers do not create a universal cross-cloud transaction system.')])
    q(2,'2b','Installing the Terraform executable also installs every provider that a later configuration might need.',[
        ('True','Providers are resolved separately for the configuration.'),
        ('False','Initialization installs the required provider packages.')],'b')
    q(2,'2c','The label of this resource is uk. Which change routes it to the aliased UK provider?',[
        ('Add provider = aws.uk.','The provider meta-argument selects the configured alias.'),
        ('Rename the resource to eu_west_2.','A resource label does not select a provider configuration.'),
        ('Set depends_on = [aws.uk].','An alias is not a managed resource dependency and this does not select its configuration.'),
        ('Add alias = "uk" inside the resource.','alias configures a provider block, not this resource.')],code='resource "aws_ssm_parameter" "uk" {\n  name = "/course/region"\n  type = "String"\n  value = "eu-west-2"\n}')
    q(2,'2c','Two AWS provider instances use different roles in the same configuration. What should the team verify before applying?',[
        ('Each instance resolves the intended identity and resources select the intended configuration.','An alias alone does not prove the credentials point at the desired account.'),
        ('Both aliases have the same name.','Aliases distinguish instances; duplicate configurations are not a verification method.'),
        ('The state file is deleted between accounts.','Deleting state can orphan resources and is not account routing.'),
        ('All resource labels include the account number.','Labels can be descriptive but do not authenticate or select an instance.')])
    q(2,'2c','A child module needs the root provider alias aws.uk. Which approach expresses that interface?',[
        ('Declare the needed alias in the child requirements and map the root configuration in the module call.','Explicit provider passing communicates the aliased configuration across the module boundary.'),
        ('Rely on the child reading a root local named uk.','Locals are scoped and do not pass provider instances.'),
        ('Add the alias to a module output.','Provider configurations are not ordinary output values.'),
        ('Assume all aliases are inherited automatically.','Aliased provider configurations need explicit handling.')])
    q(2,'2d','Why does Terraform need the binding between a resource address and a remote resource ID?',[
        ('To associate configuration instances with the objects whose changes it manages.','The address/identity mapping is a central purpose of state.'),
        ('To make every cloud object globally discoverable without permissions.','State does not grant permissions or replace service discovery.'),
        ('To turn a provider constraint into a password.','Dependency constraints and credentials have different roles.'),
        ('To guarantee that a plan never changes.','New configuration and remote drift can still produce changes.')])
    q(2,'2d','After state rm removes a tracked bucket address, which statement is correct?',[
        ('The bucket remains live unless a separate operation deletes it.','State removal forgets a relationship and does not perform cloud destruction.'),
        ('AWS immediately deletes the bucket.','state rm does not invoke the managed delete operation.'),
        ('The bucket is automatically converted into a data source.','Changing configuration block types requires an explicit edit.'),
        ('The bucket can no longer incur charges.','A still-live cloud object can still incur usage charges.')])
    q(2,'2d','Which TWO statements about Terraform state are correct? Choose two.',[
        ('It can contain sensitive values even when normal output redacts them.','Redaction alone does not remove persisted values.'),
        ('It helps retain mappings and dependency information for managed objects.','Terraform uses this information during lifecycle operations.'),
        ('It should routinely be committed alongside source code.','State needs controlled storage rather than ordinary source-control distribution.'),
        ('It is identical to desired configuration.','State records associations/observations; configuration declares intent.')],'ab')

    q(3,'3a','Which sequence best describes the normal Terraform change workflow?',[
        ('Write configuration, review a plan, then apply the reviewed change.','These are the core phases for deliberate infrastructure changes.'),
        ('Destroy state, edit cloud resources, then import every run.','That is not a normal convergence workflow and risks orphaning resources.'),
        ('Format, then assume the resources exist.','Formatting does not create infrastructure.'),
        ('Apply first, then write the desired configuration.','The configuration should express the intent before applying.')])
    q(3,'3a','An apply fails after one resource is created. What is the best next step?',[
        ('Inspect the recorded state and actual resources, fix the failure, then review a new plan.','An apply is not an all-or-nothing transaction and may leave partial progress.'),
        ('Assume every previous API call rolled back.','Terraform does not guarantee rollback of all earlier operations.'),
        ('Delete the state and retry with the same names.','That can leave existing objects unmanaged and cause name conflicts.'),
        ('Mark the entire lab complete because apply began.','Completion requires successful assertions and teardown.')])
    q(3,'3b','A fresh checkout has module calls and provider requirements. Which command prepares its working directory?',[
        ('terraform init','Initialization installs dependencies and initializes backend access.'),
        ('terraform fmt','Formatting does not install dependencies.'),
        ('terraform state list','State inspection does not prepare missing modules/plugins.'),
        ('terraform output','Output inspection does not initialize the directory.')])
    q(3,'3b','A team changes backend storage and needs to carry existing state to the new location. Which init option expresses that intent?',[
        ('-migrate-state','It requests migration of existing state to the changed backend.'),
        ('-reconfigure','Reconfiguration alone does not request copying the previous state.'),
        ('-upgrade','Dependency upgrades are not state migration.'),
        ('-backend=false','This disables backend initialization for that invocation.')])
    q(3,'3c','What does terraform validate establish by itself?',[
        ('The initialized configuration is syntactically and internally consistent.','Validation uses configuration and available schemas without proving every remote API permission.'),
        ('Every configured AWS action is allowed.','Actual permissions require authenticated operations.'),
        ('All desired resources already exist.','Validation does not deploy resources.'),
        ('The next plan must be empty.','Valid configuration may propose many changes.')])
    q(3,'3c','A configuration passes validate but plan reports AccessDenied. Which interpretation is correct?',[
        ('Static consistency did not prove the selected identity has the required API permissions.','These checks establish different properties.'),
        ('The language parser is necessarily broken.','A remote authorization failure is not evidence of parser corruption.'),
        ('Deleting state will grant the missing permission.','State changes do not change IAM authorization.'),
        ('The denied action was successfully applied.','An authorization error is not a success result.')])
    q(3,'3d','Which detailed plan exit code means a successful plan containing proposed changes?',[
        ('2','Detailed exit codes use 2 for changes.'),('0','Detailed exit 0 means no changes.'),('1','Exit 1 means an error.'),('Any nonzero code means success.','Error and change outcomes must be distinguished.')])
    q(3,'3d','A pipeline must save an execution plan for later review/apply. Which option belongs on plan?',[
        ('-out=tfplan','The option writes the saved plan artifact.'),('-refresh-only=tfplan','Refresh-only selects planning mode, not an output file.'),('-generate-state=tfplan','This is not the saved-plan output option.'),('-destroy-state','Deleting state is not planning an execution.')])
    q(3,'3d','When can -refresh=false make review less reliable?',[
        ('When relevant infrastructure changed remotely since the last recorded observation.','Skipping refresh may hide current drift.'),
        ('Whenever files are already formatted.','Formatting is unrelated to refreshing remote data.'),
        ('Only when an output is not sensitive.','Sensitivity does not determine drift visibility.'),
        ('Never; it always reads every current remote setting.','The flag explicitly skips the usual refresh phase.')])
    q(3,'3d','Why is routine use of -target discouraged?',[
        ('A targeted plan can omit other changes that a full configuration plan would show.','Targets are exceptional tools rather than complete configuration review.'),
        ('It automatically encrypts all state.','Target selection does not enable encryption.'),
        ('It selects a different AWS account.','Targets select graph objects, not credentials.'),
        ('It rewrites every resource address.','Targeting does not rename configuration addresses.')])
    q(3,'3e','Which invocation applies a saved plan file rather than planning again from current configuration?',[
        ('terraform apply tfplan','The positional file selects the saved execution plan.'),
        ('terraform apply -out=tfplan','-out belongs to plan.'),
        ('terraform plan tfplan','A saved plan is consumed by apply, not used as a positional configuration directory.'),
        ('terraform fmt tfplan','Formatting does not execute a plan.')])
    q(3,'3e','Which TWO statements about saved plan files are correct? Choose two.',[
        ('They can contain sensitive operational values and require protection.','Binary encoding is not an encryption guarantee.'),
        ('They should be regenerated when the intended configuration changes.','The reviewed artifact must correspond to the intended execution.'),
        ('They are harmless to publish because humans cannot read the binary directly.','Tooling can inspect plan contents; obscurity is not secrecy.'),
        ('Applying them performs a new unconstrained interactive plan review.','A saved plan carries the previously planned actions.')],'ab')
    q(3,'3e','An otherwise unchanged security group needs deliberate replacement. What is the preferred course workflow?',[
        ('Plan with -replace=aws_security_group.app, review, then apply the saved plan.','Replacement is included in the reviewed intent.'),
        ('Remove the address from state and assume AWS deleted the group.','Forgetting an address is not replacement or deletion.'),
        ('Use terraform taint as the required current approach.','The course uses the replacement planning option instead of deprecated taint.'),
        ('Rename all variables to force a new identity.','Variable names are not a deliberate replacement contract.')])
    q(3,'3f','What does a successful destroy of one workspace establish?',[
        ('Its managed resources were processed for destruction; unmanaged leftovers still need separate checks.','Destroy operates on the selected configuration/state scope.'),
        ('Every object in the entire AWS account is absent.','It does not enumerate or destroy unrelated infrastructure.'),
        ('All state backups on all machines were erased.','Destroy is not a universal artifact purge.'),
        ('A previously detached resource must have been deleted.','An object removed from management may remain live.')])
    q(3,'3f','A state file is stored in the course S3 backend. When should the bucket be destroyed?',[
        ('After destroying dependent workload resources and migrating/retaining the required state safely.','Deleting the backend first can prevent normal workload cleanup.'),
        ('Before the workload destroy, to avoid state locking.','Removing state storage is not a lock-contention solution.'),
        ('Whenever a plan takes more than one second.','Timing alone does not authorize deleting backend storage.'),
        ('Before checking which account is selected.','Account/backend verification comes before destructive operations.')])
    q(3,'3g','Which command detects formatting differences without rewriting configuration?',[
        ('terraform fmt -check -recursive','It checks recursively and reports differences.'),
        ('terraform fmt -recursive','This rewrites formatting.'),
        ('terraform validate -format','This is not the formatting check workflow.'),
        ('terraform apply -check','Apply is not a formatting operation.')])
    q(3,'3g','After fixing indentation with fmt, should the learner skip validate and plan?',[
        ('No; formatting does not prove configuration semantics or remote effects.','The operations serve separate purposes.'),
        ('Yes; fmt executes all provider API checks.','Formatting is a language layout operation, not a live provider check.'),
        ('Yes; fmt writes the desired cloud state.','It only rewrites configuration text.'),
        ('Only if there is a provider alias.','Alias use does not make formatting equivalent to validation.')])
    q(3,'3g','A CI formatting job should fail rather than silently modify source files. What should it run?',[
        ('fmt -check, with -recursive if it covers child directories.','This makes style differences visible without rewriting the checkout.'),
        ('apply -auto-approve','Applying infrastructure is unrelated to a formatting-only gate.'),
        ('state pull into the source files','Raw state is not formatted configuration.'),
        ('init -upgrade on every branch','Provider upgrades do not enforce style.')])
