# Course operations and recovery

The runner is designed for one learner on one machine. It binds the host port to loopback, uses a single worker for Terraform commands, and serializes operations per workspace. Every live attempt is bound to its verified AWS account and selected region; the supported primary regions are eu-west-1 (Ireland), us-east-1 (N. Virginia), and eu-west-2 (London). Domain 02 deliberately uses its fixed N. Virginia/London pair.

## AWS connections

Choose an existing profile on the startup settings page or through `tfprep setup --profile NAME`. Profiles may use a host SSO session or another credential source supported by the SDK. The app resolves the explicitly selected profile and supplies its frozen credentials to child tools, rather than inheriting an unrelated ambient identity.

For an expired SSO session, run `aws sso login --profile NAME` on the host and retry the connection. The host AWS configuration/cache is mounted read-only. Missing profile, expired session and network failures leave live work blocked; they do not count as passed validation.

Access-key mode accepts key ID, secret access key and an optional session token. It does not fall back to a profile. Keys remain in server memory and relevant child-process environments, with no database or browser-storage persistence. After server restart, reconnect before resuming a live attempt. Non-secret account/profile/region metadata and all learner work survive.

Changing credentials is blocked while a lab operation is queued/running. Each operation rechecks account identity. To clean an older attempt, reconnect the account that owns it; changing the currently selected account does not transfer ownership.

`tfprep doctor` reports the state schema, writable directories, pinned Terraform version, selected identity and read-only service permission probes in the applicable regions. Passing these probes does not prove create/delete authorization; those permissions are exercised by the lab operations. Expired identity or denied service checks stay visible as errors.

## Running and editing labs

Start a fresh attempt from its challenge page. The app copies source HCL and committed lockfiles into an attempt directory, excluding provider caches, state, plans and debug logs. Use the built-in editor or the host IDE. The reference implementation remains separate from the editable workspace.

In the lab terminal, initialize, format and validate, save and inspect `tfplan`, apply it, then make a fresh saved plan with `-detailed-exitcode`. Run `lab grade`, destroy, and finish with `lab check-cleanup`. Review the plan log before applying. A saved plan is checked against its configuration and file hash; configuration changes require a new plan.

The pre-apply guard permits only the resource types in that domain's declared cost/cleanup contract, limits managed instance count, and requires exact attempt tags. It rejects infrastructure such as NAT gateways, EKS and RDS instances before applying the saved plan.

Domain 02 also requires `terraform providers lock` with the three supported platforms. Domain 03 captures the original security group ID before a planned replacement. Domain 04 rejects public SSH and tests actual ephemeral/write-only persistence; its check-scoped data read can yield exit code 2 despite zero managed changes. Domain 07's `terraform plan -generate-config-out=generated.tf` command can produce a useful file even when planning reports errors; refine it and avoid duplicate resource declarations.

## Progress and exams

An apply grade earns 50%, and an independently verified teardown following that grade earns 100%. Merely destroying a failed starter earns a cleaned status without completion credit. Content edits before teardown invalidate stale apply verification; the domain-06 cleanup backend migration preserves the historical verification receipt while cleanup is in progress.

Mastery is separate from infrastructure completion. It requires at least 80% in each of two recent practice sessions with at least five distinct answered questions for the domain. Scores with insufficient evidence are labeled accordingly. Three inline checkpoints can cover multiple related objectives.

Mock exams have a server-persisted deadline and frozen question snapshot. Refreshing or restarting does not reset the timer. Answers and explanations stay hidden until submission; an expired mock is submitted using saved answers. Partial multi-select answers receive no credit unless the selection set exactly matches the answer.

## Teardown and interrupted work

Do not delete state to make a cleanup check pass. Keep the attempt directory after an interrupted operation. The runner marks interrupted jobs and requires explicit review/retry rather than automatically replaying destructive commands.

Try normal Terraform destroy first. Recovery inventory combines exact previously captured IDs with service-specific discovery using the attempt's names and complete ownership tags. S3, SSM, EC2 networking, Secrets Manager, IAM policy and SNS adapters provide direct checks. Permission errors remain unresolved; they are never interpreted as absence.

Preview the recovery inventory before executing deletion:

```sh
docker compose exec course python scripts/aws_reaper.py --attempt ATTEMPT_ID
docker compose exec course python scripts/aws_reaper.py --attempt ATTEMPT_ID --execute
```

The shared Project tag alone never authorizes deletion. A resource with contradictory ownership tags is refused. A missing tag can be recovered only when its exact identity had previously been verified. Recovery discovery is paginated, checks used regions, and includes IAM's global scope. The reaper removes S3 object versions/delete markers and non-default IAM policy versions when needed.

After recovery deletion, run `lab check-cleanup`. Secrets Manager forced deletion is asynchronous; retry the check if the service still reports the owned secret. Deleting only a secret version does not remove the parent secret.

## Domain 06 backend order

The bootstrap directory owns the state bucket through separate local state. Workload resources use the S3 backend only after that bucket is ready. The native lock probe deliberately creates an owned lock, verifies a real Terraform contention failure, and releases only the matching probe lock.

For cleanup: destroy the workload while the backend exists, migrate its empty state to local, remove the deliberately detached parameter through scoped recovery, then destroy the bootstrap bucket. The reaper excludes bootstrap resources by default so it cannot remove an active state backend. Complete the final inventory check only after both scopes are absent.

The runner explicitly preserves the real empty source snapshot and lineage during the return to local state because Terraform may omit copying an empty snapshot. It never treats missing state as valid empty state. If migration is interrupted, keep the source bucket: its exact state object can be retrieved privately and inspected before retrying. Do not invent an empty snapshot or remove the source bucket to bypass an inspection error.

The course does not require DynamoDB locking, HCP Terraform identity/bootstrap resources, or remote execution.

## Data retention

Plan files, state snapshots and debug logs can contain operational values. The runner gives workspace directories restrictive permissions and redacts credentials from returned logs, but it cannot sanitize arbitrary files a learner writes through an external editor. Retain them locally and avoid sharing raw captures.

After a verified cleanup, use the AWS connection/settings page's private-artifact purge control to remove plan/state/debug files while retaining HCL and saved progress. The control rejects active/unverified attempts and locally populated current state. Keep SQLite progress separately. Do not run `docker compose down -v` unless you intend to delete the saved course progress; stopping the app does not clean AWS infrastructure.

Before changing course versions, stop the server, back up its state volume, and preserve active workspaces. SQLite migrations apply on startup. The state-directory lock prevents two runner processes from concurrently owning the same progress database/worker queue.
