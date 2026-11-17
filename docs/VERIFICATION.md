# Implementation and verification ledger

Verified 16 November 2026 against the original blueprint, the accepted build plan, and the user requirement removing HCP account dependencies. All required implementation and release gates are satisfied. The delivered Docker app runs at http://127.0.0.1:8080 with fresh learner progress and an explicitly selected AWS CLI profile.

Verification receipts and screenshots are generated locally under `docs/evidence/` and excluded from Git and Docker build contexts because they can contain AWS account details, resource identifiers and local filesystem paths. Evidence paths below describe those private artifacts; they are not included in a fresh clone. Use the reproduction commands below to generate your own records.

## Release gates

The subsequent region update adds `eu-west-1` (Ireland) alongside `us-east-1` (N. Virginia) and `eu-west-2` (London). UI, API, CLI, generated connection inputs and all 19 lab/backend region constraints accept the three choices; N. Virginia remains the default. Domain 02 retains its specified US/London pair, including inventory fallback when the selected primary region is Ireland. Region-selection and Terraform-input checks are local; the historical live AWS evidence below covers US/London and does not claim an Ireland live apply.

| Gate | Authoritative evidence | Result |
| --- | --- | --- |
| G1 Reproducible runtime | Both pinned Linux ARM64/AMD64 images built successfully. `evidence/image-smoke-linux_arm64.json` and `evidence/image-smoke-linux_amd64.json` record exact image IDs, Terraform 1.12.2, AWS CLI 2.27.22, TFLint 0.57.0/AWS ruleset 0.40.0, startup timing, credential-free lessons and restart persistence. `evidence/compose-smoke.json` verifies the actual Compose mounts, persisted progress/profile metadata and credential re-entry after restart. | Passed. Warm startup is below 15 seconds; initial downloads/builds are excluded. |
| G2 Content completeness | `make check` passes: eight complete domains, eleven exercises, 24 independently authored checkpoints, 120 original questions, all 37 objectives, five current schemas and two disjoint full mocks. `objective-coverage.csv` links actual anchors, checkpoints, bank IDs, exercises and validators. Each full mock and the checkpoints cover all objectives. | Passed. Full mocks contain 57 questions; shorter 20/37-question practice runs do not claim full objective coverage. |
| G3 Terraform quality | All eight reference roots and the separate domain-06 bootstrap pass fmt, readonly init, validate and TFLint on macOS ARM64, Linux ARM64 and Linux AMD64. Native evidence: `evidence/terraform-static.json`; both Linux runs completed with all checks passing on 16 November. `evidence/starter-checks.json` verifies the intended starter failures with HCL assertions, real formatting/validation and the console evaluator. | Passed. Domain 04's input-dependent rejection is verified by separate real plans/live negative tests, rather than inferred from validate. |
| G4 Grading and credentials | 38 passing Python tests cover credential precedence, session-only keys, account binding, path/origin/command guards, exact scoring/deadlines/frozen snapshots, missing state, failed/unknown checks, real-value secret leaks, stale plans/config hashes, paid-resource rejection, denied/throttled cleanup, ownership isolation, cancellation/restart, partial imports and artifact purge. `evidence/input-contracts.json` records valid and invalid CIDR/port plans. Live profile and temporary-key connections both succeeded. | Passed. One non-failing upstream Starlette/AnyIO deprecation warning remains. |
| G5 Live labs | Every domain passed apply, grade, idempotency, destroy and direct absence verification in its supported regional configuration. Independent labs ran in both primary regions; domain 02 verified its US/default and London/alias together. Domain 03's final runs changed a private TCP 8443 rule before replacement. Domain 04 compared the actual live secret against real retained artifacts. Domain 08 remained local with no HCP dependency. | Passed. See accepted attempts below and all retained JSON receipts. |
| G6 Cleanup resilience | `evidence/live-recovery.json` records observed/canceled apply and destroy operations, missing-tag recovery from previously verified IDs, state removal refusing false completion, S3 versions/delete markers, default dry run, recovery of unimported fixtures, and preservation of another live attempt. Domain 06 separately verified S3 lock contention, moved IDs, removed-but-retained objects, migration and ordered bootstrap teardown. `evidence/final-cleanup.json` audits every known verification attempt directly against AWS. | Passed. All verification resources are absent, including resources from failed runs. |
| G7 Product behavior | Seven passing credential-free browser tests cover responsive navigation, every lesson/exercise, keyboard alternatives, profile/key forms, saved answers/deadlines and shorter mocks. The live browser journey passed profile onboarding, editing, AWS SNS apply/grade, reload, destroy and 100% cleanup; see `evidence/browser-live.json` and screenshot. CLI integration tests use the same API/services, and the real container CLI verified profile access and doctor diagnostics. `evidence/state-drills.json` records actual isolated list/show/pull/mv/rm commands. | Passed. The editor reset found during the live journey was fixed and the complete journey rerun successfully. |
| G8 Documentation | README, operations/recovery, cost assumptions, per-lab permission templates, original PDF/review, objective traceability and reproducible commands are present. The packaged content checker and delivered Compose dashboard were verified. The original nine-page PDF checksum remains unchanged. | Passed within the documented account/platform boundaries below. |

## Accepted live coverage

| Domain | us-east-1 attempt | eu-west-2 attempt |
| --- | --- | --- |
| 01 | `5be686155d8646f0` | `1621244a8c794c1a` |
| 02 | `28353c008b7f418a` | Same run verifies both regions |
| 03 | `4f65d2b193064cef` | `86e314dd5fd34100` |
| 04 | `b908bd1b1e5e4dfe` | `c7523683c75c479b` |
| 05 | `70f4ea88915d492f` | `08d57940805248d6` |
| 06 | `fae00fd2fa9b4c3d` | `d98f0a004a5844f2` |
| 07 | `d055a7c46c214e7b` | `94aa79999501428c` |
| 08 | `6ce3d856b80f4c18` | `49bf5a575ae04366` |

An additional domain-08 run (`8913828c9dd94adc`) verified real apply/grade/destroy inside Docker using the read-only mounted host profile. The browser journey used a separate isolated runner. Live JSON records include account, region, attempt, versions, configuration/plan hashes, assertion results and cleanup outcome. Earlier failed runs remain visible with their cleanup receipts; a failed run is not counted as accepted coverage.

Domain 04 permits check-scoped data reads when a receipt-bound saved plan proves zero managed-resource and root-output changes. Other labs require detailed plan exit code 0. This behavior was observed on the pinned Terraform 1.12.2 and is explained in the blueprint review.

## Reproduce

### Debugging supplement update

The 16 November update adds `/troubleshooting`: a method for investigating an existing repository, seven interactive incidents, and an isolated local repository workshop with four intentional defects. Configuration, lint, dependency, expression, API/credential, locking/state and replacement diagnosis are covered. It is a 60–90 minute supplement to the eight-domain course.

`make check test` passes (38 tests), and the expanded browser suite passes all ten checks, including the new guide, all case feedback, keyboard operation and mobile layout. `make check-troubleshooting` and the same checker inside both final Linux images pass 23 checks each: real failing diagnostics, repairs, local apply, idempotency, destroy and reference checks. No AWS credentials or resources are needed by the workshop. CI now runs it separately from the cloud suites.

The local update record (`evidence/debugging-update.json`) identifies the new source hashes and image IDs; the guide screenshot (`evidence/debugging-guide.png`) and mobile screenshot (`evidence/debugging-mobile.png`) capture the delivered app. Learner progress and workspaces were retained. The original `release-audit.json` remains the historical initial-release record; existing AWS lab evidence still applies to the unchanged eight labs. The selected AWS connection needs reconnecting for future cloud labs; the debugging section works without it.

### Verification commands

Credential-free checks:

```sh
make check test test-browser
make check-terraform check-starters state-drills
make check-troubleshooting
make image image-smoke
```

With a deliberately selected profile and the local server running:

```sh
TFPREP_AWS_PROFILE=your-course-profile make test-live
.venv/bin/python scripts/live_recovery.py --profile your-course-profile
TFPREP_AWS_PROFILE=your-course-profile make test-browser-live
```

Recovery state surgery uses the native runner's own workspace; the live browser command starts an isolated server. These commands create and clean uniquely owned test resources. Credentials and live secret values are absent from evidence. The delivered Compose learner database is separate from the retained verification databases/workspaces.

## Boundaries and costs

This is a single-learner local app. Profiles use host credential sources supported inside the container; an expired SSO session requires host login and reconnection. Permission templates are reviewable starting points, not policies proven under every organization's boundaries/SCPs. The user-selected profile was used for the actual live verification.

Budget under **US$0.10 per full short course run** with prompt cleanup, or under **US$1 for repeated verification runs**. These are estimates for course resources before account credits/taxes, not measured billing totals or account-wide caps. See [cost assumptions](costs.md). No required lab creates compute instances, NAT gateways, RDS/EKS, public IPs or paid HCP infrastructure.
