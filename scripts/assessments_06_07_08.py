"""State, maintenance and HCP conceptual assessment scenarios."""


def author(q):
    q(6,'6a','A root configuration has no remote backend configuration. Where does the default local backend normally persist its state?',[
        ('In a local terraform.tfstate file in the applicable working-directory layout.','The default backend uses local filesystem state.'),
        ('Automatically in an HCP workspace without login or configuration.','Hosted state requires a configured integration.'),
        ('Inside .terraform.lock.hcl.','The lockfile manages provider selections, not resource state.'),
        ('Only in provider memory until the next run.','Persistent state is needed across operations.')])
    q(6,'6a','A team shares local state by emailing it after every apply. What is a better operational design?',[
        ('Use an appropriate controlled shared backend and account for its locking/access behavior.','Shared controlled storage avoids ad hoc distribution and coordination.'),
        ('Commit every secret-containing snapshot to a public repository.','That exposes state data without giving the team controlled access and coordinated writes.'),
        ('Delete state after every apply.','Terraform would lose mappings to existing objects.'),
        ('Assume multiple local copies coordinate writers automatically.','Separate local copies do not give the team one shared state.')])
    q(6,'6b','Which setting enables native S3 backend locking?',[
        ('use_lockfile = true','It opts into the separate S3 lock object.'),
        ('encrypt = true alone','Encryption and locking are separate features.'),
        ('versioning = true in the workload provider','Backend locking is not enabled by this provider setting.'),
        ('sensitive = true on a root variable','Sensitivity does not coordinate state writers.')])
    q(6,'6b','Which TWO statements about S3 lockfiles are correct? Choose two.',[
        ('The lock object uses the state key with a .tflock suffix.','The lock has a distinct object identity.'),
        ('The runtime needs the relevant read/write/delete permissions for the lock object.','Lock acquisition and release need explicit access.'),
        ('Native locking requires a DynamoDB table.','S3 native locking removes that requirement.'),
        ('Turning on bucket encryption always turns on lockfiles.','Locking remains an explicit backend option.')],'ab')
    q(6,'6b','Another confirmed-live apply owns the state lock. What should a second operator do?',[
        ('Wait or investigate the owning operation before attempting recovery.','The lock protects concurrent state writers.'),
        ('Immediately delete the lock because their plan is important.','Removing a live lock can permit conflicting writers.'),
        ('Delete the state bucket.','Destroying state storage is not a contention solution.'),
        ('Rename all resource addresses and retry in the same state.','Changing addresses does not resolve ownership of an active lock.')])
    q(6,'6b','What is the status of the legacy DynamoDB-based S3 locking setting on this course baseline?',[
        ('It is deprecated; native S3 lockfiles are the course pattern.','The new pattern uses use_lockfile rather than requiring a new lock table.'),
        ('It is the only supported way to lock S3 state.','Native S3 locking is supported.'),
        ('It is enabled by the AWS resource default_tags block.','Provider resource tags do not configure backend locks.'),
        ('It makes S3 state encryption unnecessary.','Lock coordination and encryption have distinct roles.')])
    q(6,'6c','Why does the course bootstrap its S3 backend bucket with separate local state?',[
        ('The backend must exist before the workload can initialize against it, and its cleanup must happen last.','Separating bootstrap ownership avoids circular storage dependencies.'),
        ('Terraform cannot manage S3 buckets.','The AWS provider can manage S3 buckets.'),
        ('Local state is guaranteed to contain no sensitive values.','Local state still requires protection.'),
        ('A bucket can never be deleted after state migration.','It can be cleaned after dependent state has been handled safely.')])
    q(6,'6c','Which information belongs in the course partial backend file?',[
        ('The owned bucket, state key and region, while credentials come from the selected connection.','Non-secret backend identity can be configured separately from secrets.'),
        ('Committed long-lived access keys.','Credentials should not be embedded in checked-in backend configuration.'),
        ('Root resource references as unrestricted backend arguments.','Backend initialization does not work like ordinary resource expression evaluation.'),
        ('A generated ephemeral password as the state object key.','A temporary secret is not a stable backend identity.')])
    q(6,'6c','Why can terraform_remote_state create a broader access concern than its exposed outputs suggest?',[
        ('The consumer needs access to the underlying snapshot, which may contain additional sensitive data.','Output selection is not a replacement for backend access control.'),
        ('It automatically grants write access to every cloud provider.','It does not create universal provider permissions.'),
        ('It removes all state from the producer.','Reading outputs does not delete producer state.'),
        ('It always starts a remote apply.','It reads state outputs rather than inherently applying producer configuration.')])
    q(6,'6d','A parameter value was edited remotely. What does apply -refresh-only do?',[
        ('Update Terraform observations and applicable outputs in state without restoring the HCL value in AWS.','Refresh-only accepts observation rather than reconciling desired infrastructure.'),
        ('Rewrite HCL to the remote value automatically.','Terraform does not edit configuration to match drift.'),
        ('Always recreate the parameter under a new name.','Refresh-only updates state; it does not restore the configured setting in AWS.'),
        ('Delete the parameter from the account.','Observation is not destruction.')])
    q(6,'6d','Which declaration preserves a tracked object when changing its resource address?',[
        ('A moved block with the previous and new addresses.','It declares the address refactor while retaining the object mapping.'),
        ('A new resource block with no state relationship.','That can appear as destroy/create rather than a known move.'),
        ('A different output description.','Output documentation does not move resource state.'),
        ('A provider alias whose name matches the new resource.','Provider configuration selection does not rename resource addresses.')])
    q(6,'6d','What should the learner expect after this removal is applied?',[
        ('The remote parameter stays live but Terraform no longer manages its old address.','destroy=false explicitly retains the remote object.'),
        ('The parameter must be deleted from AWS immediately.','That contradicts destroy=false.'),
        ('The parameter becomes encrypted because it is removed.','State ownership changes do not supply this encryption behavior.'),
        ('Every other resource in state is removed too.','The declaration targets the specified address.')],code='removed {\n  from = aws_ssm_parameter.detached\n  lifecycle { destroy = false }\n}')
    q(6,'6d','The course state list is empty but the inventory still finds a detached parameter. Is teardown complete?',[
        ('No; cloud absence for the owned inventory still needs to be proven.','An empty state can coexist with live unmanaged resources.'),
        ('Yes; empty state always means no cloud objects remain.','This confuses state associations with actual resource existence.'),
        ('Yes; removed resources cannot incur service usage.','Remote objects remain subject to service behavior and pricing.'),
        ('Only the shared Project tag matters, even for unrelated attempts.','Cleanup must follow the exact attempt scope.')])
    q(6,'6d','Which evidence proves a moved refactor preserved identity?',[
        ('The before/after remote ID is unchanged while the state address changes as intended.','Both the address refactor and the persistent cloud identity matter.'),
        ('The new resource label contains the word moved.','A label is not execution evidence.'),
        ('The old state file was deleted.','Check the resource IDs to show they stayed the same; deleting the record cannot prove it.'),
        ('A replacement produced a different ID.','That demonstrates replacement rather than preserving the same object.')])

    q(7,'7a','Which parts of a declarative import serve different purposes?',[
        ('to selects the Terraform address; id identifies the existing provider object.','Address and remote identity are separate inputs.'),
        ('to is the AWS secret; id is the provider version.','That does not describe import semantics.'),
        ('Both fields must be identical for every resource type.','Addresses and provider IDs use different formats.'),
        ('to chooses a module registry version.','Import targets are not module source version constraints.')])
    q(7,'7a','A bucket and IAM policy already exist. Which import ID pair is appropriate for these AWS resources?',[
        ('Bucket name and IAM policy ARN.','The resource types have their own provider import identifiers.'),
        ('Bucket ARN and policy short display name in all cases.','That swaps the identifiers required by these resource imports.'),
        ('The HCL file names for both objects.','File names do not identify remote AWS objects.'),
        ('The current AWS access key and secret.','Credentials authenticate; they are not resource import IDs.')])
    q(7,'7a','What is the correct role of plan -generate-config-out=generated.tf?',[
        ('Generate a starting resource configuration for applicable import targets that do not yet have configuration.','Generated configuration still needs review and refinement.'),
        ('Guarantee that all generated settings are the final desired abstraction.','Generated code can include defaults or arguments needing adjustment.'),
        ('Delete existing resources before adoption.','Import is intended to adopt existing objects rather than replace them.'),
        ('Encrypt the existing state snapshot.','Configuration generation is not a state encryption operation.')])
    q(7,'7a','Which TWO checks support a safe adoption of an existing resource? Choose two.',[
        ('Compare the existing remote identifier with the imported state identity.','This proves the intended object was adopted.'),
        ('Review the plan for unwanted changes/replacements and reach a no-change plan when appropriate.','Adoption should preserve the desired existing object.'),
        ('Assume a same-named resource declaration automatically imported it.','Adding the resource block alone does not import the existing object.'),
        ('Delete all setup records immediately, even if import failed.','Setup records are needed for verification and cleanup.')],'ab')
    q(7,'7b','Which command inspects attributes of one tracked object?',[
        ('terraform state show ADDRESS','This inspects the selected tracked resource instance.'),
        ('terraform state rm ADDRESS','This tells Terraform to forget the object instead of just showing its attributes.'),
        ('terraform destroy ADDRESS','That is not the state-inspection command and the positional usage is not the intended workflow.'),
        ('terraform init ADDRESS','Initialization does not use this form for inspecting one object.')])
    q(7,'7b','What does terraform state pull return?',[
        ('The raw snapshot from the selected backend.','It reads the backend state representation and can expose sensitive contents.'),
        ('Only public root output names with every value removed.','The snapshot can contain much more than public output names.'),
        ('A new cloud resource identifier with no state read.','It is a state read operation.'),
        ('A complete IAM permissions report.','State pulling does not audit the active role permissions.')])
    q(7,'7b','A learner needs to change a mapping without deleting the cloud object. Which TWO mechanisms can serve appropriate refactoring intents? Choose two.',[
        ('A deliberate state mv operation.','It changes a state address/mapping without performing cloud deletion.'),
        ('A declarative moved block.','It expresses the refactor in reviewable configuration.'),
        ('Destroying the original object first.','That does not preserve the same remote object.'),
        ('Deleting the entire state and all backups.','That loses management relationships rather than describing the intended mapping change.')],'ab')
    q(7,'7c','What does TF_LOG_PATH configure?',[
        ('The destination path for enabled Terraform logging.','It selects where applicable logs are written.'),
        ('The verbosity level by naming a directory DEBUG.','A path is not the log-level setting.'),
        ('The AWS CLI profile.','Credential selection uses different configuration.'),
        ('The module source package.','Logging configuration does not select module sources.')])
    q(7,'7c','Why should raw provider debug logs stay private?',[
        ('They can contain sensitive request/response information beyond normal output redaction.','Debugging material needs controlled access and retention.'),
        ('They always contain only harmless resource labels.','Provider logs can include request and response details, including secrets.'),
        ('The .log extension automatically encrypts them.','A filename extension provides no confidentiality.'),
        ('They are safe to commit whenever a variable is marked sensitive.','Sensitivity is not a universal log sanitization guarantee.')])
    q(7,'7c','Core TRACE output is noisy; you need AWS provider DEBUG messages. Which setting isolates the relevant component?',[
        ('TF_LOG_PROVIDER=DEBUG','This controls provider logging separately.'),
        ('TF_LOG_PATH=provider','That chooses a path rather than component verbosity.'),
        ('AWS_REGION=DEBUG','A region variable is not a Terraform logging selector.'),
        ('TF_VAR_provider=DEBUG','An input variable does not control Terraform log verbosity.')])

    q(8,'8a','A local Terraform CLI queues a run that executes in HCP Terraform infrastructure. How should the workflow be described?',[
        ('CLI-driven trigger with remote execution.','Trigger and execution mode are separate dimensions.'),
        ('Local execution solely because the CLI initiated it.','The location of the initiating client does not determine provider execution location.'),
        ('A mandatory agent run.','Nothing states that an agent executes this run.'),
        ('A VCS-only speculative plan.','The described trigger is the CLI, not necessarily VCS or speculative.')])
    q(8,'8a','What is a benefit of a hosted run environment for a collaborating team?',[
        ('A shared operational workflow with recorded plans/runs and controlled execution settings.','The platform provides a common context rather than relying only on individual terminals.'),
        ('It removes all need for provider credentials.','The execution environment still needs appropriate authentication.'),
        ('It guarantees every run is free and requires no permissions.','Capabilities, pricing and permissions remain relevant.'),
        ('It makes state contain no resource identities.','State still tracks managed objects.')])
    q(8,'8a','An HCP workspace uses local execution. Where do Terraform provider operations execute?',[
        ('On the local execution machine.','Local execution differs from hosted remote operations.'),
        ('Always inside an HCP-hosted worker.','That describes remote rather than local execution.'),
        ('Inside the web browser only.','The browser is not the ordinary Terraform provider runtime.'),
        ('In a random AWS region selected by policy.','Execution mode is not a random region selector.')])
    q(8,'8a','A run must reach private infrastructure unavailable from public hosted workers. Which execution option may address that access need?',[
        ('An appropriately connected HCP Terraform agent.','Agents execute jobs on infrastructure with the needed connectivity.'),
        ('A different output description.','Output text does not supply network reachability.'),
        ('Removing all provider requirements.','A missing provider cannot implement the infrastructure operation.'),
        ('Publishing private credentials in a plan comment.','Exposing credentials does not create a sound connectivity design.')])
    q(8,'8b','Which pair belongs to OPA policy enforcement in HCP Terraform?',[
        ('advisory and mandatory','OPA uses these enforcement labels with applicable override permissions.'),
        ('soft-mandatory and hard-mandatory only','Those labels are associated with Sentinel rather than the OPA pair.'),
        ('init and destroy','Those are CLI operations, not policy enforcement levels.'),
        ('sensitive and ephemeral','Those are value-handling concepts, not OPA enforcement levels.')])
    q(8,'8b','An advisory policy fails. What is its normal enforcement effect?',[
        ('Report the failure without interrupting the run solely for that advisory policy.','Advisory policies provide non-blocking feedback.'),
        ('Always delete the workspace.','A policy failure does not authorize workspace deletion.'),
        ('Automatically replace every noncompliant object.','Policy evaluation is not automatic configuration repair.'),
        ('Silently grant administrator access to the author.','Policy outcomes do not grant such permissions.')])
    q(8,'8b','Which TWO capabilities support collaboration and governance? Choose two.',[
        ('Team access permissions for relevant platform resources.','Access boundaries govern who can perform operations.'),
        ('A private registry for organizational reuse of reviewed packages.','A registry helps share appropriate reusable components.'),
        ('A guarantee that no user ever needs to inspect a plan.','Governance does not replace plan review.'),
        ('One plaintext password shared publicly among all users.','Public shared credentials undermine controlled access.')],'ab')
    q(8,'8b','A mandatory policy blocks a run. Can any user automatically override it?',[
        ('No; override behavior depends on framework/settings and the user permissions.','Mandatory does not mean every user has an override right.'),
        ('Yes; typing a different variable always grants policy-override permission.','Configuration values do not create platform permissions.'),
        ('Yes; all read-only users can apply blocked changes.','Read access is not equivalent to policy override/apply access.'),
        ('Only users with an AWS provider alias named admin.','A Terraform provider alias name does not grant HCP platform authority.')])
    q(8,'8c','What is the main organizational relationship between projects and workspaces?',[
        ('Projects group workspaces while workspaces retain their own state and run context.','Grouping does not imply one merged state snapshot.'),
        ('Every project must contain exactly one resource.','Projects are not individual resource objects.'),
        ('A workspace is a local Git branch in every execution mode.','The platform workspace concept is broader than a Git branch.'),
        ('Projects replace all team permissions.','Access controls still apply to the organization and relevant resources.')])
    q(8,'8c','A setting must be shared across workspaces in one project but not all projects. Which feature fits?',[
        ('An appropriately project-scoped variable set.','Scope controls which workspaces receive the shared values.'),
        ('A provider alias with the project name.','Provider aliases do not distribute platform variable sets.'),
        ('One global unscoped state file for all infrastructure.','Sharing state is not the intended variable-distribution mechanism.'),
        ('A speculative plan output with an access key.','A preview plan is not a sound shared-secret distribution method.')])
    q(8,'8c','What does a workspace run trigger connect?',[
        ('A successful apply in a source workspace with queuing an applicable dependent workspace run.','It connects workflow progression across workspaces.'),
        ('Two resource addresses into one permanent ID.','It does not merge resource identities.'),
        ('All remote state snapshots into a single file.','Triggered workspaces keep their state boundaries.'),
        ('An IAM policy directly to a module variable default.','That is not the run-trigger relationship.')])
    q(8,'8c','Do run triggers automatically publish every upstream output as a downstream variable?',[
        ('No; input/data-sharing interfaces still require explicit configuration.','Workflow triggering is distinct from value exchange.'),
        ('Yes; every output is copied regardless of scope.','A run trigger starts a run; it does not copy every output into the next workspace.'),
        ('Yes; this is why sensitive outputs can be published publicly.','Sensitivity and access still need deliberate handling.'),
        ('Only if both workspaces have the same display color.','Display styling has no input-sharing semantics.')])
    q(8,'8d','A VCS pull request should preview a change without performing its apply. Which run type fits?',[
        ('A speculative plan.','It provides a proposal preview rather than an applyable production run.'),
        ('A forced destroy.','Destruction is not the requested preview behavior.'),
        ('A raw state removal operation.','State surgery does not preview a configuration change.'),
        ('A provider installation only.','Installation does not show the proposed infrastructure diff.')])
    q(8,'8d','For an actual CLI integration with HCP Terraform, what does a cloud block identify?',[
        ('The applicable hosted organization/workspace association for the workflow.','The block connects the CLI workflow to platform context.'),
        ('A required AWS access key stored in source.','Cloud integration settings are not a reason to commit provider credentials.'),
        ('The replacement for every provider source address.','Providers still declare their own requirements.'),
        ('A guarantee that all runs use agent mode.','The workspace execution settings determine execution mode.')])
    q(8,'8d','Which TWO statements distinguish workflow triggers? Choose two.',[
        ('VCS-driven workflows respond to applicable source-control events.','Version-control integration supplies the trigger.'),
        ('API-driven workflows can be initiated through platform API operations.','API initiation is distinct from a local CLI or VCS event.'),
        ('CLI-driven always means provider execution occurs locally.','The trigger does not fix the execution mode.'),
        ('A speculative plan must automatically apply on every pull request.','Speculative plans are previews without that apply behavior.')],'ab')
    q(8,'8d','Why should a team separately configure remote-run AWS authentication?',[
        ('A hosted execution environment does not automatically inherit the initiating machine local AWS profile.','Credentials must be available through an appropriate remote authentication setup.'),
        ('The provider never makes AWS calls during remote execution.','Remote providers still need to access AWS APIs.'),
        ('The local .aws folder is always embedded in every saved plan.','That is not the integration contract and should not be assumed.'),
        ('A workspace name alone authorizes all AWS API operations.','Choosing a workspace name does not give the run AWS permissions.')])
