# Terraform Associate 004 refresher

A local, hands-on course for engineers returning to Terraform. It includes eight lessons and AWS challenges, eleven interactive exercises, 24 checkpoints covering all 37 objectives, 120 original assessment questions, and two 60-minute mock exams. Budget approximately **12–16 hours** to complete it.

Terraform is pinned to **1.12.2**. HCP Terraform topics are taught through local simulations; **no HCP organization, workspace, login or token is required**.

The additional **Debugging & problem solving** section teaches a method for taking over an existing repository: orient, reproduce, classify, isolate, repair and prove. Allow another **60–90 minutes** for the guide, seven interactive diagnostic cases and a broken local repository workshop. It covers configuration, lint, dependency installation, expressions, credentials/API failures, locks, state and unexpected changes. The workshop creates no AWS resources and requires no credentials. Open it from the sidebar or at `/troubleshooting`.

## Start with Docker

Install and start Docker Desktop or an equivalent Docker engine with Compose. From this directory:

```sh
docker compose up --build -d
```

Open [the course at localhost:8080](http://127.0.0.1:8080). On the AWS connection screen, choose either a named **AWS CLI profile** or **IAM access keys**, optionally with a session token. The app verifies caller identity before enabling live lab attempts. Lessons, exercises and assessments work without AWS credentials.

The first build downloads pinned base images, tools and packages and can take several minutes depending on the network. The 15-second startup target applies after the image is built: the tested Compose restart became healthy in 3.46 seconds. Docker Compose 2.24.3 and both Linux ARM64/AMD64 images were verified; the root Compose file uses Compose's `include` feature.

Available primary lab regions are **eu-west-1 (Ireland)**, **us-east-1 (N. Virginia)** and **eu-west-2 (London)**. N. Virginia remains the default. Domain 02 uses a fixed N. Virginia/London pair to teach provider aliases.

For SSO profiles, sign in on the host first:

```sh
aws sso login --profile your-course-profile
```

The container mounts the host AWS configuration read-only. Entered access keys stay in server memory and must be entered again after restarting or disconnecting. The app stores non-secret connection metadata only.

Learner HCL persists in `workspaces/`; SQLite progress persists in the Compose `course_state` volume. Stopping containers does not destroy AWS resources or erase progress.

```sh
docker compose stop
docker compose start
```

Use `TFPREP_PORT=8082 docker compose up -d` if port 8080 is already occupied. The host bind is loopback only.

## Use the CLI

The container includes `tfprep`, which calls the same service as the browser:

```sh
docker compose exec course tfprep setup --profile your-course-profile
docker compose exec course tfprep doctor
docker compose exec course tfprep start 01
docker compose exec course tfprep run 01 -- init
docker compose exec course tfprep run 01 -- plan
docker compose exec course tfprep run 01 -- apply
docker compose exec course tfprep run 01 -- plan
docker compose exec course tfprep validate 01
docker compose exec course tfprep run 01 -- destroy
docker compose exec course tfprep teardown-check 01
```

Fix the starter configuration before applying. `tfprep setup --keys` uses hidden prompts for access keys and the optional session token; do not place secrets in command-line arguments. For multiple attempts, supply `--attempt ATTEMPT_ID`. For example, `tfprep run 03 --attempt ATTEMPT_ID --replace aws_security_group.app -- plan`.

Passing live apply assertions earns 50%. Completion reaches 100% only after a previously verified apply, successful destroy, empty state, and direct absence checks across the owned resource inventory. A failed starter that is merely cleaned up earns no completion credit.

## Local development

Use Python 3.12 and npm. Setup installs pinned Python/web dependencies and a project-local Node runtime:

```sh
make setup
make terraform
make web
make serve
```

The native app uses `.state/` for progress and `workspaces/` for lab files. Neither directory is tracked by Git. The web development server is optional; for Vite hot reload, start the API with `TFPREP_DEV_ORIGIN=http://127.0.0.1:5173` and run `npm run dev` in `runner/web` using the local Node binary in PATH.

## Verify the build

```sh
make check
make test
make test-browser
make check-terraform
make check-starters
make state-drills
make check-troubleshooting
make image
make image-smoke
```

Browser checks require Chromium installed for the pinned Playwright version. Static Terraform validation and lint need downloaded providers and the pinned TFLint/AWS ruleset; the Docker image includes the lint toolchain. Checks performed in restricted execution environments may require permission for Terraform plugin localhost sockets.

Live checks create and destroy uniquely owned AWS resources. They require a deliberately selected profile and the running local server:

```sh
TFPREP_AWS_PROFILE=your-course-profile make test-live
```

Live evidence is generated locally under `docs/evidence/`. Receipts and screenshots can contain AWS account details, resource identifiers and local paths, so this directory is excluded from Git and Docker build contexts. It is not included in a fresh clone. A failed or skipped live check does not satisfy a release gate. Domain 04 permits scoped-check data reads only when its saved plan proves zero managed-resource and root-output changes; other labs require detailed plan exit code 0.

The current gate-by-gate status and remaining live checks are recorded in [the verification ledger](docs/VERIFICATION.md). Deliberate recovery checks use `.venv/bin/python scripts/live_recovery.py --profile your-course-profile`; the complete browser/AWS journey uses `TFPREP_AWS_PROFILE=your-course-profile make test-browser-live`. Both create and clean explicitly owned AWS test resources and are separate from the credential-free suite.

`make state-drills` runs list/show/pull/mv/rm exercises against an isolated `terraform_data` fixture and removes its temporary directory afterward. It creates no AWS resources. Mock exams default to 57 questions; the assessment screen also offers shorter practice runs. The CLI equivalent is `tfprep exam --mock A --questions 20`.

## Operations and source material

- [Operations and recovery](docs/operations.md)
- [Proposed AWS hosting and timed lab cleanup](docs/AWS_HOSTING_PLAN.md)
- [AWS permission templates](docs/iam/README.md)
- [Cost assumptions](docs/costs.md)
- [Build plan](BUILD_PLAN.md)
- [Blueprint verification and corrections](BLUEPRINT_VERIFICATION.md)
- [Objective coverage](objective-coverage.csv)

The original [course blueprint PDF](<Refresher Course Blueprint.pdf>) is retained. HashiCorp exam details can change; confirm registration logistics with the official certification site. This is independent preparation material rather than a reproduced exam question bank.
