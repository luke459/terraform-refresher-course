# Terraform Associate 004 course build plan

Build the complete local refresher course described in [the blueprint](<Refresher Course Blueprint.pdf>): eight lessons and AWS challenges, eleven interactive exercises, a Docker runtime, a shared web/CLI validator, persistent mastery tracking, cleanup tooling, and at least 120 original exam questions. Apply the findings in [BLUEPRINT_VERIFICATION.md](BLUEPRINT_VERIFICATION.md). The implementation and required release verification are complete; evidence is tracked in [docs/VERIFICATION.md](docs/VERIFICATION.md).

**Confirmed scope change:** no HCP Terraform organization, workspace, login or token is required. Domain 08 covers HCP exam concepts through local simulations and runs its SNS challenge locally in AWS using the same selected profile or access keys as the other domains. This supersedes the PDF's remote HCP lab and all former HCP access prerequisites.

## Delivery decisions

| Area | Proposed implementation |
| --- | --- |
| Repository | Use this workspace as the monorepo root; keep the original PDF. Initialize Git during implementation. |
| Runtime | Debian-based `python:3.12-slim-bookworm`, pinned by digest at P0; Linux AMD64 and ARM64 builds. Terraform **1.12.2**, verified download checksums. |
| Tool versions | Candidate AWS provider **5.92.0**, random **3.7.2**, committed lockfiles per root configuration. Freeze AWS CLI v2, TFLint, AWS ruleset, Python and web dependencies to tested exact versions at P0; never download unversioned latest during image startup. |
| Backend and CLI | FastAPI, Pydantic contracts, Python AWS SDK, SQLite, and Typer `tfprep`; one service layer supplies both interfaces. A worker executes long tasks and records durable jobs. |
| Frontend | React/TypeScript with Vite; compile trusted bundled MDX into lesson pages at build time. Serve built assets from the API image. |
| Access | Host publish `127.0.0.1:8080`; server binds `0.0.0.0` inside the container. Restrict browser origins and protect mutation endpoints against cross-origin requests. |
| Persistence | Host `./workspaces:/workspaces`; named `course_state:/var/lib/tfprep` for SQLite and receipts; AWS host config/cache read-only. Read user HCL from per-attempt workspace directories. |
| AWS onboarding | At course startup, accept either a user-provided AWS CLI profile name or IAM access key ID and secret access key, with an optional session token. Verify the selected credentials before enabling live labs. |
| Learning modes | Lessons, widgets, quizzes and HCP simulations work without cloud credentials. Live AWS labs require STS/account/region preflight. |
| AWS regions | Primary configurable to `eu-west-1` (Ireland), `us-east-1` (N. Virginia), or `eu-west-2` (London). Lab 02 retains its fixed N. Virginia/London pair. Inventory stores actual regions and global IAM scope. |

The provider versions above are frozen and have passed schema checks and live secrets round trips in both supported AWS regions. AWS 5.92 documents `secret_string_wo` and `secret_string_wo_version`; random 3.7.2 documents ephemeral passwords. Lab 02 retains its educational `~> 5.80` constraint with a compatible committed resolution. [AWS provider source](https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v5.92.0/website/docs/r/secretsmanager_secret_version.html.markdown), [random provider source](https://raw.githubusercontent.com/hashicorp/terraform-provider-random/v3.7.2/docs/ephemeral-resources/password.md).

## Target repository layout

```text
docker/                 Dockerfile, docker-compose.yml, toolchain manifest
runner/api/             API routes, service layer, worker, SQLite migrations
runner/web/             lessons, diffs, exercises, labs, mastery, timed exams
runner/cli/             tfprep commands using shared services
curriculum/domain-01/   lesson.mdx, challenge.md, starter/, solution/, validator.yaml
... domain-02..08/      same contract; domain-05 also contains child modules
curriculum/domain-06/bootstrap/   independently managed state backend
exam-bank/              questions_004.json, question schema, mock blueprint
schemas/                lesson, challenge, validator, result, question schemas
scripts/                aws_reaper.py, content/coverage checks, smoke checks
tests/                  fixtures, unit, integration, browser, live-lab suites
docs/                   operations, IAM policies, cost estimates, troubleshooting
workspaces/             ignored learner copies, plans, state, and private logs
.github/workflows/      offline checks, image builds, explicitly enabled live checks
```

Use one primary implementation language for application logic. The five roles in the PDF become workstreams with clear ownership below; a single implementer can follow the same dependency order.

## Build sequence and effort

Estimates are engineering effort for one experienced implementer, including curriculum authoring and review. They exclude waiting for account access. Total **36–48 working days**; optional independent workstreams can overlap after their shared contracts are stable.

| Phase | Owner and effort | Dependencies | Concrete work and exit evidence |
| --- | --- | --- | --- |
| P0 Contracts and compatibility | Platform + lab + curriculum, 3–4 days | None | Freeze schemas, objective IDs, tool manifest and package locks. Bootstrap a minimal image on both architectures. `terraform version -json` reports 1.12.2. `terraform providers schema -json` confirms the secret write-only attribute/version counter and ephemeral random resource. Verify named-profile, IAM access-key, SSO and temporary-credential paths, including conflicting inherited credentials, using fixtures and designated test credentials. Review the cost/IAM model. |
| P1 Platform and persistence | Platform, 3–4 days | P0 | Build Compose volumes, health routes, SQLite migration, startup AWS connection form/CLI prompts, credential diagnostics and workspaces. Offer profile or access-key selection before the first live lab; credential-free lessons remain available. Restart preserves learner files and progress; access keys must be re-entered. Benchmark warm startup under 15 seconds, excluding build/pull and external STS latency; report full first-run time separately. |
| P2 Runner and grading engine | Runner + lab, 5–6 days | P0, P1 | Implement job execution, HCL parsing, Terraform JSON handling, AWS adapters and local HCP simulations, result schema, command receipts, scoped inventory and completion transitions. Demonstrate lab 01 end to end through CLI and UI, including teardown. Test failures, canceled jobs, stale evidence, retries and permission errors. |
| P3 Complete vertical slice | Runner + curriculum + assessment, 3–4 days | P2 | Ship domain 01 lesson, diff, both widgets, three checkpoints, challenge, solution and first eight bank questions. A learner completes it from a clean container; accessibility, browser/CLI equivalence, restart and negative-grading tests pass. |
| P4 All AWS labs | Lab + platform, 8–10 days | P3 | Finish domains 02–08 starter/solution/validators; implement backend migration cleanup, ephemeral leak proof and domain-08 local SNS verification. Live-test every solution and intentionally broken variants. Domains except 02 run independently in both supported primary regions; lab 02 runs cross-region. Cleanup evidence is mandatory for each attempt. |
| P5 Complete curriculum and interactions | Curriculum + runner, 6–8 days | P0, P3; release waits for P4 | Finish all eight MDX lessons, eleven widgets and 24 checkpoint questions. Each lesson opens with “2023 vs 2026” and “3-Year Catch-Up”, with accurate historical context. Link all 37 objective rows to anchors and evidence; include Vault and HCP conceptual topics that do not fit the AWS labs. |
| P6 Assessment and mastery | Assessment + runner, 4–6 days | P3; question authoring can follow P0 | Finish 120 original scenario questions with explanations and sources. Add practice, 60-minute mock, review flags, exact-set multi-select scoring, persisted deadlines, reload recovery, domain/objective results and mastery tracking. Verify bank allocation and complete browser exam flow. |
| P7 Release verification | All workstreams, 4–6 days | P4, P5, P6 | Run all release gates below, fresh install and full eight-domain learner journey. Validate reaper recovery for interrupted applies, publish cost assumptions and operation instructions, and capture a versioned release evidence manifest. |

Dependency path: **P0 → P1 → P2 → P3 → P4 → P7**. P5 and P6 join at P7. No phase exit means the corresponding build work is already implemented.

## AWS connection at course startup

The startup screen and `tfprep setup` offer two connection methods:

- **AWS CLI profile:** enter the profile name, such as `course-sandbox`. Resolve that named profile from the read-only host AWS configuration mount, including an existing SSO session or supported role configuration. Save only the profile name and non-secret connection metadata. Expired SSO sessions require host login and a retry.
- **IAM access keys:** enter access key ID and secret access key, plus an optional session token for temporary credentials. Mask secret/token fields; CLI entry uses hidden prompts rather than command-line secret arguments. Keep the credential bundle in server memory for the active course session and pass it only to the relevant SDK clients and child-process environments. Do not save it to SQLite, Terraform files, browser storage, logs, or the container image. Re-enter credentials after an application restart or disconnect.

Provide a **Test connection** action using STS `GetCallerIdentity`, then display the account ID and caller ARN and let the learner choose the primary lab region. Successful identity verification enables live-lab entry; each lab still checks its required service permissions. Missing/invalid credentials leave lessons and quizzes accessible and give a specific connection error. Do not create AWS resources as part of the connection test.

Use the explicitly selected method consistently for the AWS SDK, AWS CLI, Terraform providers, S3 backend, validators and reaper. Isolate conflicting inherited credentials: profile mode must not silently use ambient access keys, and access-key mode must not silently fall back to a profile. Keep each attempt bound to its verified account and regions; block operations under a different account and preserve ownership records when credentials expire or change. Replacing credentials for the same account re-runs identity checks before resuming work.

Local startup credentials configure all eight AWS challenges. Domain 08 simulates HCP workflows locally without contacting HCP Terraform or uploading credentials.

## Shared runner contracts

Freeze these before authoring eight independent validators:

1. **Content:** domain ID, objective IDs, lesson anchors, prerequisites, estimated time, resource types, region scope, costs/assumptions, three checkpoints, setup/cleanup instructions, and named exercises. Reference solutions remain separate from editable learner copies.
2. **Execution:** persisted attempt/job IDs, working directory, typed operation and argument vector, environment allowlist, timeout, cancellation, exit status, timestamps, tool versions and content hash. Avoid shell interpolation. Only course-defined operations are available; do not expose an arbitrary command API. Serialize mutating Terraform operations per workspace, including UI/CLI requests and worker restarts.
3. **Validation:** `schema_version`, check ID/type, required phase, typed assertions, resource selectors and prerequisites. Keep `hcl_ast`, `tf_state_json`, and `aws_cli` compatibility from the PDF; use parsed HCL traversals, explicit **JMESPath** for JSON queries, and typed AWS operation/argument definitions behind `aws_cli`. Add structured plan and artifact-leak check types. Unknown types/keys fail schema validation.
4. **Results:** `pass`, `fail`, `error`, `blocked`, or `skipped`, with sanitized evidence references and actionable messages. A credential error, unsupported check, missing state, timeout, or skipped live check can never count as a pass. Progress records include attempt/config hashes so later edits invalidate stale validation.
5. **Persistence:** SQLite migrations cover learners, attempts, jobs, checks, owned resources, command receipts, checkpoint answers, exam sessions and answers. Store secrets in neither SQLite nor receipts. Restrict state/plan/debug artifact permissions and give users a local retention/purge control.

Expose `tfprep setup`, `tfprep doctor`, `tfprep start <domain>`, `tfprep run <domain> -- <operation>`, `tfprep validate <domain>`, `tfprep teardown-check <domain>`, `tfprep status`, and `tfprep exam`. The run command maps approved Terraform operations/flags to the shared executor and captures receipts; graded command exercises must use it or the equivalent UI action. Direct container CLI use remains available for exploration, with missing graded evidence reported explicitly. API equivalents cover AWS connection/test/disconnect, domains/lessons, attempts, jobs and event streaming, validation, progress and exam sessions. Connection endpoints return only non-secret status/account metadata. Return an asynchronous job ID for long operations; browser reconnect resumes from persisted results. CLI accepts explicit attempt selection when more than one exists.

`doctor` verifies binaries, writable mounts, state schema, selected AWS profile/account, region permissions. Do not print credential values. Successful STS is required for live work, while general application readiness remains independent of credential availability.

## Completion and cleanup model

An attempt follows **not started → active → apply verified (50%) → cleanup pending → complete (100%)**. Errors retain the last valid state; edits after apply verification require revalidation. Quiz mastery and infrastructure cleanup are separate measures.

Every taggable lab resource gets `Project=tf-004-prep`, `ManagedBy=terraform`, and unique learner/lab/attempt ownership tags. Provider aliases receive the same defaults. Track untaggable children by exact parent/resource IDs and record resources created by setup scripts before Terraform imports them. Names include account/attempt-safe suffixes; IAM ownership is account-global.

Completion requires a successful destroy receipt, successful inspection of the correct backend, no remaining managed resources for the attempt, and direct absence checks against all inventoried resource IDs. Paginate service inventories, check all used regions, and treat `AccessDenied` as unresolved cleanup. Resource Groups Tagging API cannot find all untagged resources, so it is supplementary. [Tagging API scope](https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/API_GetResources.html).

`scripts/aws_reaper.py` defaults to dry run and reports the exact account, regions, owned IDs and dependency order. An explicit execute mode only deletes resources matching the attempt inventory and ownership rules; it never selects everything with the shared Project tag. Prefer ordinary Terraform destroy, then use service-specific recovery adapters for S3 objects/versions/delete markers, IAM policy versions, networking dependencies, secrets and SNS. An interrupted creation may leave resources outside the inventory: reconcile exact unique names/tags with service APIs before recovery.

Backend bootstrap resources have their own ownership scope. Keep them until dependent state is migrated or removed. A domain can complete with declared shared prerequisites still present; full-course cleanup separately verifies their removal. Secret deletion uses lab-only zero recovery windows and bounded absence polling. [Secrets Manager deletion](https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_DeleteSecret.html).

## Domain implementation and acceptance

Each domain ships the exact lesson/challenge/starter/solution/validator structure in the PDF, a visible cost estimate, setup and teardown instructions, and three checkpoint questions. [objective-coverage.csv](objective-coverage.csv) maps every sub-objective to existing lesson anchors, checkpoint IDs, question-bank IDs, exercises and validators.

| Domain and lab | Required implementation | Acceptance evidence |
| --- | --- | --- |
| 01 `lab-01-iac-baseline` | Supply `create_s3_and_ssm.sh`; learner converts it to a versioned S3 bucket and standard SSM metadata parameter. Build Architecture Triage and Idempotency Simulator. | Bucket versioning Enabled, exact SSM value, second **`plan -detailed-exitcode` = 0**, then absence checks. Test drift predictions and resource action symbols. |
| 02 `lab-02-multi-provider` | Default US and `uk` London AWS providers, paired SSM parameters, `~> 5.80`, committed lockfile. Build Constraint Solver and Lockfile Inspector. | Correct alias bindings and parameters in both regions. Record `providers lock -platform=linux_amd64 -platform=linux_arm64 -platform=darwin_arm64`; readonly initialization succeeds on matching platforms. Both regions clean. |
| 03 `lab-03-safe-workflow` | Repair formatting/syntax in VPC/subnet/security group stack, save/apply plan, use `-replace` on a security group. Use an out-of-band rule change as the controlled drift scenario; no EC2 instance required. Build CLI Flag Lab. | Fmt/validate pass; saved-plan receipt matches applied plan; replacement is visible in structured plan and execution receipt, and the security group ID changes. Reject taint-based completion. Teach refresh-only, refresh=false and target caveats. |
| 04 `lab-04-contracts-and-ephemeral` | Typed object input, `for_each` security groups/rules, CIDR/port validation, precondition, **postcondition**, scoped-data check, ephemeral random password → Secrets Manager write-only field and version counter. Build Evaluation Order Visualizer and State Leak Inspector. Add Vault delivery comparison. | HCL and provider schema assertions pass. Valid input succeeds; bad CIDR/ports and failed contracts produce expected outcomes. Check warnings cannot silently pass grading. Fetch exact live secret only into validator memory and scan real state/plan JSON plus retained workspace artifacts; leaking fixture fails, correct fixture passes. Secret parent disappears after teardown. |
| 05 `lab-05-modular-network` | Refactor into `modules/app-tier`, typed inputs, `for_each` module calls for dev/stage, outputs to root SSM summary. Build Scope Debugger; teach registry/Git/local/S3 sources and version semantics. | Both environment hierarchies/tags and exact module instance addresses exist; output summary matches live resources. Negative fixture catches illegal child/root scope references. Both environments clean. |
| 06 `lab-06-native-s3-locking` | Separate encrypted/versioned bootstrap bucket; workload backend uses lockfile/encryption and partial config. Migrate state, demonstrate lock contention, moved refactor, refresh-only drift observation and normal desired-state reconciliation. Add a removed-without-destroy exercise. Build Lock Contention Lab. | Observe lock acquisition/contention/release, configured lock-object permissions, S3 state object and unchanged moved resource ID. No course DynamoDB table in plan/inventory. Explain refresh-only's remaining diff. Removed resource stays live until explicit owned cleanup. Destroy workload, move empty workload state back to local while backend exists, then empty versioned bucket and destroy bootstrap from its separate local state. |
| 07 `lab-07-declarative-import` | Setup script creates tagged IAM policy and S3 bucket; capture IDs before import. Use import blocks and `-generate-config-out`, repair generated HCL, inspect state and capture private provider debug logs. Build Log Triage. | Existing IAM policy ARN and bucket name match imported identities; no replacement; final detailed-exit plan is 0. Sanitized evidence confirms provider log entries. State list/show/mv/rm/pull drills use disposable fixtures; imported cloud resources and setup artifacts are cleaned. |
| 08 `lab-08-hcp-concepts` | Build Governance & Hierarchy Sandbox, framework-specific policy behavior, variable sets, run triggers, execution-mode and speculative-plan simulations. Deploy an SNS topic locally using Terraform 1.12.2 and the selected AWS connection. | Clearly label conceptual HCP simulations. Verify SNS state/live identity, idempotency and complete AWS teardown. No HCP account, organization, workspace, token, cloud block or remote execution is required. |

Domain 08 retains the full HCP exam syllabus as conceptual content. Simulated organization/project/workspace and remote-run examples must be distinguishable from the actual local SNS apply. No HCP network checks or identity bootstrap resources belong in the required course workflow.

## Assessment and learner experience

Allocate the initial **120 bank questions** across domains **8, 12, 18, 30, 12, 14, 10, 16**. These are course practice weights, not published exam weights. Require at least two bank questions per objective and additional code-reading scenarios for dependencies/lifecycle, conditions, ephemeral values and HCP organization. The 24 inline checkpoints are additional to the 120-question bank.

Question records include stable ID, primary/secondary objectives, type, prompt, optional code, choices, exact correct selection set, rationale for every choice, difficulty, source URL, compatible Terraform/provider version and review date. Use original questions; do not reproduce exam dumps. Split 120 into two fixed non-overlapping 57-question mock sets with domain allocations **4, 6, 8, 14, 6, 6, 5, 8** each, leaving six practice questions. Support configurable mock length; 57 is a simulation setting rather than a verified official count. Official sample formats support true/false, single-answer and multi-answer prompts. [Question formats](https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-questions-004).

Each mock independently covers all 37 objectives while respecting its domain allocation. Persist an authoritative 60-minute deadline and selected answers; reloading cannot restart the timer. Freeze a question snapshot per session so content updates cannot change an in-progress exam. Hide answers until mock submission, provide flag/review navigation, then explain every choice. Label the score as practice performance, not an official passing prediction. Suggested mastery: at least 80% across two recent practice attempts with five distinct questions for that domain; show insufficient evidence explicitly. Infrastructure completion remains governed by teardown.

All widgets support keyboard alternatives to dragging, readable diff labels, accessible controls, and deterministic examples. The UI includes dashboard, lesson/diff, lab instructions/logs/results, cleanup status, question practice, timed exam and review. Code and logs are escaped before display. Restart, browser reconnect and an expired AWS session must preserve learner work.

## Cost and account prerequisites

Use a designated AWS sandbox with permission to create, inspect and delete S3, standard SSM parameters, VPC/subnets/security groups, IAM policies, Secrets Manager secrets, and SNS topics. Produce per-lab permission policies and separate bootstrap privileges; avoid requiring administrator credentials for normal labs. HCP concepts require no account or credentials.

Every challenge declares expected resource count, maximum intended duration, both regional cost estimates, pricing date, cleanup behavior and account-credit assumptions. Target sub-cent short runs where feasible, but record gross usage before Free Tier credits and account-specific net cost separately. Secrets Manager bills storage/API use, so `0.00` cannot be an unconditional assertion. Bound resource counts and polling; prohibit NAT Gateways, EKS and RDS instances. The essential labs require no compute instances. [Secrets Manager pricing](https://aws.amazon.com/secrets-manager/pricing/).

AWS live checks require an authorized account during implementation. Missing credentials should block those checks explicitly while allowing local work. Live execution uses only the user-selected profile and uniquely owned lab resources.

## Release gates

| Gate | Required proof |
| --- | --- |
| G1 Reproducible runtime | Both image architectures build from pinned manifests/checksums. Terraform 1.12.2, AWS CLI v2 and pinned lint tools work. Warm healthy startup meets measured <15s target. First-run timing and host requirements are documented. |
| G2 Content completeness | Eight complete domain trees, eleven working exercises, 24 checkpoints, all 37 objective rows linked to existing anchors/evidence, at least 120 valid/reviewed bank questions and two disjoint mocks. |
| G3 Static Terraform quality | All solutions pass fmt, backend-disabled initialization, validate and lint under the frozen toolchain. Broken starters fail only their declared expected checks. Lockfiles initialize readonly on supported platforms. |
| G4 Grading correctness | Each check has passing and failing fixtures; missing/empty/wrong state, failed conditions, secret leaks, stale plan receipts, command spoofing, AWS AccessDenied, pagination and throttling cannot yield false completion. Both startup credential methods work; conflicting ambient credentials cannot override the selection, secrets are absent from persisted artifacts/logs, and account changes block existing attempts. |
| G5 Live lab correctness | Apply/validate/idempotency/destroy cycle for all eight labs; independent single-region labs run in each supported primary region, domain 02 in both together, IAM globally. Domain 08 uses a live local SNS lab with separately labeled HCP simulations. Record account, attempt, versions, commit/content hash, sanitized assertions and cleanup outcome. |
| G6 Cleanup resilience | Interrupt apply and teardown, remove a tag, remove an address from state, leave S3 versions and an import setup resource; recover only owned resources. Other attempts survive unchanged. Backend prerequisites are removed in correct order at full-course teardown. |
| G7 Product behavior | Browser and CLI produce equivalent results. Persisted files/progress and exam deadline survive restarts. Complete learner journey, keyboard exercise alternatives and protected local mutation endpoints pass. |
| G8 Documentation | Fresh-install instructions, startup profile/access-key selection, session-token handling, credential re-entry and profile/SSO expiry recovery, local AWS costs, IAM policies, bootstrap/state recovery, reaper dry run/execute, troubleshooting and known account capability limits are usable from a clean checkout. |

Implementation CI should separate credential-free checks from manually enabled live suites. Suggested release commands to implement are `make check`, `make test`, `make test-browser`, `make image-smoke`, and `make test-live`; these targets are implemented. `make state-drills` verifies disposable local state operations, `make test-browser-live` runs the complete browser/AWS journey with an explicit profile, and `scripts/live_recovery.py --profile NAME` exercises deliberate cleanup failures against the native runner. Credential-free CI must never report G5/G6 as passed when cloud tests were skipped.

## First implementation milestone

Start P0 with schemas and a toolchain probe, then build the platform and domain 01 vertical slice through cleanup. Do not author the other seven validators until both CLI and UI can consume the same structured lab-01 results. The first reviewable delivery should contain the pinned container, schema fixtures, doctor diagnostics, persistent progress, a complete domain 01 experience, and sanitized proof of its apply/validate/destroy cycle.
