"""Configuration contracts and module boundary assessment scenarios."""


def author(q):
    q(4,'4a','A configuration must inspect an existing VPC without taking responsibility for deleting it. Which block type fits?',[
        ('A provider data source.','A data block reads information without declaring managed ownership of that object.'),
        ('A managed resource with the same name.','That declares a desired managed object rather than merely querying it.'),
        ('An output block alone.','An output publishes an expression but does not itself implement the provider query.'),
        ('A removed block with destroy=true.','That expresses removal/destruction intent, not an ordinary read.')])
    q(4,'4a','What distinguishes resource and data blocks?',[
        ('Resources declare managed lifecycle objects; data sources query provider information.','Their ownership and lifecycle roles differ.'),
        ('Data sources never contact an API.','Provider data sources can make API reads.'),
        ('Resources are evaluated only by the browser.','Terraform and provider plugins execute the configuration.'),
        ('A data source automatically imports the returned object.','Querying an object is not adoption into a managed resource.')])
    q(4,'4b','What useful relationship does this expression establish?',[
        ('A value reference and an implicit dependency on the VPC.','Terraform can infer the ordering from the referenced resource attribute.'),
        ('Only a comment for the plan renderer.','The expression contributes to the actual dependency graph.'),
        ('An automatic dependency on every VPC in AWS.','It refers to a specific configuration instance.'),
        ('A new provider configuration.','Provider configuration requires its own declaration.')],code='vpc_id = aws_vpc.course.id')
    q(4,'4b','A new resource ID appears as known after apply in a plan. What does that mean?',[
        ('The value is not yet known and may become available during execution.','Planned unknowns represent values that cannot yet be computed.'),
        ('The configuration is necessarily invalid.','Unknown values are a normal part of planning.'),
        ('The resource already has no dependencies.','Unknown values often arise from dependencies that have not run.'),
        ('The ID can be used as a for_each key immediately.','Instance keys must be known at the required planning stage.')])
    q(4,'4c','The same input is set through TF_VAR_environment and an explicit -var option in a CLI run. Which setting wins?',[
        ('The explicit command-line variable setting.','Command-line variable assignments have higher precedence than environment assignments.'),
        ('The environment variable always wins.','Environment defaults do not override an explicit CLI assignment.'),
        ('The variable default always wins.','Defaults are used when no higher-precedence value supplies the input.'),
        ('Terraform must create two resources.','Input precedence does not itself multiply resource instances.')])
    q(4,'4c','What is the purpose of a root output?',[
        ('Expose a selected configuration result to users or consumers.','Outputs publish chosen expressions from the module interface.'),
        ('Grant AWS permissions to every caller.','Publishing an output does not change IAM policies.'),
        ('Hide all resource attributes from state.','Outputs do not remove resource attributes from state.'),
        ('Install a provider alias.','Provider configuration is a separate concern.')])
    q(4,'4c','A child module receives a typed object variable. Why add a validation rule as well?',[
        ('To constrain acceptable values beyond their structural type.','A number/string type alone does not enforce a particular port range or CIDR rule.'),
        ('To eliminate all provider API errors.','A local contract cannot guarantee every remote condition.'),
        ('To copy root locals into child scope automatically.','Scope still requires explicit input passing.'),
        ('To mark every field ephemeral.','Validation does not create ephemeral semantics.')])
    q(4,'4d','Which collection best represents unique unordered subnet IDs?',[
        ('set(string)','A set provides uniqueness without positional identity.'),
        ('list(string) solely because it removes duplicates automatically','Lists preserve ordering and do not inherently remove duplicates.'),
        ('tuple([string,number])','That is a fixed heterogeneous sequence, not a homogeneous collection of IDs.'),
        ('string','A scalar does not model a collection of IDs.')])
    q(4,'4d','Which TWO statements about structural types are correct? Choose two.',[
        ('An object can declare named attributes with different types.','Each object attribute has its own declared type.'),
        ('A tuple can declare types for fixed ordered positions.','Tuple element positions are part of its structure.'),
        ('A map must use numeric-only keys.','Terraform maps use string keys.'),
        ('A set provides stable numeric indices for its members.','Sets do not provide positional identity.')],'ab')
    q(4,'4d','What does map(object({ port = number, cidr = string })) express?',[
        ('String-keyed entries whose values share a named port/CIDR object shape.','The map keys can identify services while each value has typed attributes.'),
        ('An ordered tuple containing a number and a string.','The outer type is a map, not a tuple.'),
        ('A provider configuration for every TCP port.','Types describe values; they do not declare provider instances.'),
        ('A set that automatically rejects every invalid CIDR string.','The string type alone does not validate CIDR syntax.')])
    q(4,'4e','Why can using count over a reorderable list create unexpected address changes?',[
        ('Numeric instance addresses follow indices rather than the logical names of list entries.','Removing/reordering entries can change which logical item occupies an index.'),
        ('count always stores a separate state file per element.','Repeated instances normally share the selected root state.'),
        ('for_each never uses state.','Both repetition mechanisms produce tracked instances.'),
        ('Lists cannot contain strings.','String lists are valid; identity is the issue here.')])
    q(4,'4e','Which value is suitable for for_each instance keys?',[
        ('A known map of non-sensitive service names.','Stable known keys let Terraform identify instances during planning.'),
        ('New resource IDs available only after apply.','Those keys are not known when instances must be identified.'),
        ('A sensitive password string.','Sensitive values are not appropriate exposed instance keys.'),
        ('A secret generated by an ephemeral operation.','Temporary secrets do not establish stable instance identity.')])
    q(4,'4e','What is dynamic intended to generate?',[
        ('Repeated nested blocks accepted by a resource or similar block schema.','Dynamic blocks construct supported nested configuration blocks.'),
        ('Arbitrary lifecycle meta-argument blocks.','Meta-arguments must be processed before normal dynamic expansion.'),
        ('A new Terraform provider executable.','Provider plugin construction is unrelated to HCL dynamic blocks.'),
        ('A guaranteed number of root resource instances.','count/for_each on the resource address that need, not a dynamic nested block.')])
    q(4,'4e','A policy document is assembled from Terraform values. Which approach avoids hand-escaping JSON strings?',[
        ('Build a Terraform object and use jsonencode.','jsonencode produces JSON from the typed value.'),
        ('Concatenate unescaped user input into JSON text.','Unescaped interpolation can produce invalid or unintended JSON.'),
        ('Mark the JSON output sensitive to validate syntax.','Sensitivity controls display, not JSON syntax.'),
        ('Use state rm before writing the document.','State removal has no role in serialization.')])
    q(4,'4f','A resource already references another resource ID. Should you add depends_on only to duplicate that relationship?',[
        ('Usually no; the reference already expresses the dependency.','Use explicit dependencies for hidden behavioral relationships that values do not express.'),
        ('Always; references never affect ordering.','References are how Terraform normally infers graph dependencies.'),
        ('Only if the files are alphabetically ordered.','File ordering does not establish graph ordering.'),
        ('Always; depends_on eliminates every unknown value.','Broad dependencies can instead produce more conservative plans.')])
    q(4,'4f','What practical constraint can prevent create_before_destroy from succeeding?',[
        ('The old and new objects cannot coexist because of name uniqueness or quotas.','Replacement order does not override the provider API constraints.'),
        ('The configuration is in two different .tf files.','Files within the same module form one configuration.'),
        ('There is a root output.','An output does not inherently prevent overlapping replacement.'),
        ('The provider source contains a namespace.','Provider source naming is unrelated to simultaneous object existence.')])
    q(4,'4f','A resource has prevent_destroy=true. Does that create a permanent AWS deletion-protection control?',[
        ('No; it is a Terraform lifecycle rule while the applicable declaration remains.','It is not an independent cloud-side protection flag.'),
        ('Yes; it survives deleting the resource declaration forever.','Removing the declaration removes that configuration rule.'),
        ('Yes; it grants IAM denies across every tool.','Terraform lifecycle settings do not rewrite account-wide permissions.'),
        ('Only for objects with a data source.','Data source use does not turn it into a cloud-side control.')])
    q(4,'4f','Another system owns updates to one tag after creation. What can ignore_changes express?',[
        ('Ignore selected attribute changes during update planning while retaining the resource lifecycle.','It can delegate specific update concerns without forgetting the object.'),
        ('Never send that attribute when creating the resource.','Ignore behavior does not mean the initial creation value is irrelevant.'),
        ('Remove the entire object from state.','That is state removal, not selective ignored updates.'),
        ('Stop AWS billing for the object.','Lifecycle planning does not control billing independently of resources.')])
    q(4,'4f','A hidden behavioral dependency cannot be represented by an attribute reference. Which meta-argument can express it?',[
        ('depends_on','It adds the explicit dependency edge.'),
        ('sensitive','A sensitivity mark is not an ordering dependency.'),
        ('description','Documentation alone does not add a graph edge.'),
        ('alias inside a resource','Provider aliases are configured elsewhere and do not express this dependency.')])
    q(4,'4g','A precondition uses a value known only after another resource is created. When can its evaluation occur?',[
        ('It can be deferred until apply when the required value becomes known.','The condition is evaluated when its inputs are available at the appropriate stage.'),
        ('Always before any plan can be produced.','Not every required value is known during planning.'),
        ('Never; Terraform silently deletes the condition.','Unknown inputs do not mean the contract is discarded.'),
        ('Only during terraform fmt.','Formatting does not evaluate runtime contracts.')])
    q(4,'4g','A top-level check assertion fails but the provider operation itself succeeds. What is Terraform behavior?',[
        ('Report a check warning without making the assertion a blocking resource contract.','Checks have non-blocking assertion behavior; external grading may still reject the outcome.'),
        ('Always roll back every created resource.','Terraform checks do not provide universal transactional rollback.'),
        ('Rewrite the check to true.','Terraform does not modify the expression to hide failures.'),
        ('Remove the failed resource from state.','A failed check does not imply state removal.')])
    q(4,'4g','What is an appropriate use of a resource postcondition?',[
        ('Verify a guarantee about the resulting resource or read result and block dependent work on failure.','Postconditions check expected outcomes at the relevant lifecycle stage.'),
        ('Guarantee every expression is checked only after apply.','Known values and data reads can allow earlier evaluation.'),
        ('Generate resource names after destroy.','This is not their role.'),
        ('Disable every provider-side validation.','Terraform contracts do not replace provider API constraints.')])
    q(4,'4g','Which TWO statements about custom conditions are correct? Choose two.',[
        ('Input validation can reject values that have the right type but violate a domain rule.','Structural types and semantic conditions are complementary.'),
        ('Preconditions and postconditions were available before Terraform 1.3.','They were introduced in Terraform 1.2.'),
        ('check assertions always have the same blocking behavior as preconditions.','Top-level checks emit warnings for assertion failures.'),
        ('Every condition must use only literal constants.','Conditions can refer to applicable input/resource values.')],'ab')
    q(4,'4g','A learner supplies port 70000 to a variable requiring ports 1..65535. What should a failed validation mean?',[
        ('The operation is rejected with the configured validation message.','Input validation enforces the semantic boundary.'),
        ('Terraform silently clamps it to 65535.','A failed condition does not define automatic correction.'),
        ('The invalid value is accepted because its type is number.','Correct type alone does not satisfy the validation rule.'),
        ('The entire AWS account is destroyed.','A failed input contract does not authorize unrelated destructive actions.')])
    q(4,'4h','A sensitive password variable is passed to a normal persisted resource argument. What risk remains?',[
        ('The value may still be stored in Terraform state or plan artifacts.','Sensitive marks normally affect display, not persistence.'),
        ('It is automatically encrypted with a different key per output.','The sensitive argument does not create this encryption behavior.'),
        ('The provider is forbidden from receiving it.','The provider still needs applicable values to perform operations.'),
        ('It is automatically changed into an ephemeral resource.','Ephemeral behavior requires the appropriate declarations and compatible contexts.')])
    q(4,'4h','Which release timeline matches the course baseline?',[
        ('Ephemeral values/resources in 1.10 and write-only arguments in 1.11, both usable on 1.12.','These capabilities predate the course runtime minor version.'),
        ('All secret-handling features first appeared in 1.12.','The individual feature introductions were earlier.'),
        ('Write-only arguments require Terraform 0.12 only.','Their core support requires Terraform 1.11 or later.'),
        ('Ephemeral values require no core support if a provider has a field named password.','Core and provider capabilities both matter.')])
    q(4,'4h','Why does the Secrets Manager write-only example include a non-secret version counter?',[
        ('It signals intentional updates because Terraform does not retain the old write-only value for comparison.','Incrementing the companion counter requests the relevant update.'),
        ('It stores the password in base64 instead.','The counter is not encoded secret storage.'),
        ('It makes the secret free to retain forever.','Version counters do not alter service pricing.'),
        ('It selects the AWS CLI profile.','Provider credentials are a separate configuration concern.')])
    q(4,'4h','Which TWO destinations can accept appropriate ephemeral values? Choose two.',[
        ('A provider-supported write-only managed-resource argument.','That field is designed to consume a value without persisting it in Terraform artifacts.'),
        ('A compatible provider configuration context.','Ephemeral values can be used in supported transient contexts such as provider configuration.'),
        ('Any ordinary root output by adding a comment.','Comments do not change output persistence semantics.'),
        ('A normal persisted argument with no ephemeral support.','An ephemeral value cannot be routed into every persistent context.')],'ab')
    q(4,'4h','A password is retrieved from Vault and then written to an ordinary persisted argument. Does Vault as the source prove the state is secret-free?',[
        ('No; downstream handling determines whether Terraform persists the value.','A secret source does not automatically make all consumers ephemeral.'),
        ('Yes; provider state never stores values that originated in Vault.','The origin does not impose such a universal guarantee.'),
        ('Yes; Terraform does not receive secret values from providers.','Applicable provider operations can supply values to expressions.'),
        ('Only if the variable name contains vault.','Variable naming has no persistence semantics.')])
    q(4,'4h','Which evidence is strongest for the course secrets lab?',[
        ('Verify the real write-only/ephemeral path and compare the actual live secret against nonempty state, plan and retained artifacts, with a leaking negative fixture.','The check tests actual persistence rather than relying on a display mark or missing object alone.'),
        ('Search for a made-up resource type that is absent even when nothing was deployed.','That can pass without proving the required flow was used.'),
        ('Check that the word sensitive occurs in any file.','The text alone does not establish non-persistence.'),
        ('Assume a successful apply guarantees a leak-free log.','Execution success does not prove artifact secrecy.')])

    q(5,'5a','Which module source clearly refers to a local child directory?',[
        ('./modules/app-tier','The explicit relative path selects a local directory.'),
        ('hashicorp/aws','That is a provider source address, not this local module path.'),
        ('app-tier without a path prefix','It does not express the same explicit local path.'),
        ('var.generated_module_path as an arbitrary runtime expression','Module source selection is not an unrestricted runtime string expression.')])
    q(5,'5a','A team consumes a module from a Git repository. What should it review for reproducibility?',[
        ('The repository source and selected ref or commit.','A moving branch and a fixed revision have different repeatability properties.'),
        ('Only the AWS provider alias name.','Provider routing does not pin the Git module content.'),
        ('Only .terraform.lock.hcl because it locks every module.','The provider lockfile does not lock module packages.'),
        ('Only the order of .tf file names.','File ordering does not select a remote module revision.')])
    q(5,'5a','After changing a module source declaration, what prepares the new dependency before normal validation/planning?',[
        ('Run terraform init and review the subsequent plan.','Initialization installs the selected module package.'),
        ('Run terraform fmt and skip initialization.','Formatting does not install changed sources.'),
        ('Delete the managed AWS resources first.','Changing dependency installation does not itself require destructive pre-cleanup.'),
        ('Use state rm for every child resource.','Forgetting resources is not an initialization strategy.')])
    q(5,'5b','A child module references local.environment defined only in the root. What is the right repair?',[
        ('Declare a child input and pass the root value in the module call.','Module scopes are separate and inputs express the boundary.'),
        ('Rename the root file to variables.tf.','File names within a module do not export scope into another module.'),
        ('Read root.local.environment with a special prefix.','This is not an automatic cross-module scope mechanism.'),
        ('Add depends_on to copy the local value.','Ordering does not supply a missing input variable.')])
    q(5,'5b','Several ordinary .tf files in one directory contribute to the same module scope.',[
        ('True','Scope changes through module boundaries, not ordinary file splitting.'),
        ('False','Moving declarations between ordinary files in the same directory does not isolate their scope.')],'a')
    q(5,'5b','Why should a reusable child module declare typed inputs?',[
        ('To make its accepted interface explicit and validate caller shape/values appropriately.','Inputs are the module argument contract.'),
        ('To expose every internal resource automatically.','Outputs, not typed inputs, publish selected results.'),
        ('To eliminate any need for output declarations.','Inputs and outputs serve different directions of the interface.'),
        ('To grant cross-account permissions.','Type declarations do not change IAM permissions.')])
    q(5,'5c','How should a root read the VPC ID published by one non-repeated child module app_tier?',[
        ('module.app_tier.vpc_id','This reads the child output.'),
        ('module.app_tier.aws_vpc.app.id','Child resource internals are not directly exposed through the module namespace.'),
        ('var.app_tier.vpc_id automatically','The module call does not implicitly create that root variable.'),
        ('provider.app_tier.vpc_id','Provider configurations are not module output namespaces.')])
    q(5,'5c','The module call uses for_each with dev and stage keys. Which reference selects dev output vpc_id?',[
        ('module.app_tier["dev"].vpc_id','for_each produces keyed module instances.'),
        ('module.app_tier[0].vpc_id','Numeric indexing is not the keyed instance selection shown here.'),
        ('module.dev.app_tier.vpc_id','The call name and instance key use a different address structure.'),
        ('aws_vpc.module.app_tier.dev','This does not address the published child output.')])
    q(5,'5c','Which TWO practices support clear module composition? Choose two.',[
        ('Pass required values through explicit inputs.','This keeps scope and dependencies visible.'),
        ('Expose selected results through outputs.','A deliberate output interface avoids reaching into internals.'),
        ('Require every child to read a root local by convention.','Root locals are not implicitly in child scope.'),
        ('Use file names to decide resource creation order.','Terraform uses dependency expressions rather than ordinary file ordering.')],'ab')
    q(5,'5d','Which source supports the module version argument for version selection?',[
        ('A Terraform module registry source.','Registry module packages support the version argument.'),
        ('Every arbitrary Git URL.','Git sources select revisions through their source ref syntax.'),
        ('A local folder based on its modification time.','Local source selection does not use registry version resolution.'),
        ('An AWS provider alias.','Provider aliases are not module source versions.')])
    q(5,'5d','How can a Git module source select tag v1.2.0?',[
        ('Use an appropriate Git source URL with ?ref=v1.2.0.','The ref query selects the Git revision.'),
        ('Add version = "1.2.0" as if it were a registry source.','That version mechanism is specific to registry module sourcing.'),
        ('Put v1.2.0 in the AWS_PROFILE value.','Credentials do not select module revisions.'),
        ('Rename the child output to v1_2_0.','Output names do not pin source code.')])
    q(5,'5d','What must a team remember about .terraform.lock.hcl when reviewing a module upgrade?',[
        ('It records provider dependency selections, not a general module package lock.','Module version/ref controls must be reviewed separately.'),
        ('It guarantees that a moving Git branch never changes.','A provider lockfile cannot freeze a Git branch.'),
        ('It automatically signs private module content.','It is not a general private-module signature mechanism.'),
        ('It makes plan review unnecessary.','A dependency change still deserves execution-plan review.')])
