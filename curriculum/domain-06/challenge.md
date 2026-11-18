# Lab 06: move state without losing track of your resources

This lab has a few stages, so follow the order below. Start with the `legacy` and `detached` SSM parameters in local state. You'll move workload state to S3, rename one resource with `moved`, and use `removed` to stop tracking the other without deleting it.

The `bootstrap` directory manages a separate encrypted, versioned S3 bucket. Keep it available until the workload no longer needs its state.

1. Initialize the starter workload, save and review a plan as `tfplan`, then apply it. Run `lab capture-baseline` before changing addresses.
2. Initialize, plan and apply the bootstrap bucket using `terraform -chdir=bootstrap ...`. Save its plan as `tfplan` too. It uses separate local state.
3. Run `lab migrate-remote`. The runner creates partial backend settings with `use_lockfile=true` and `encrypt=true`, without storing credentials in them.
4. Use the reference refactor in root `main.tf`: move `legacy` to `metadata`, and detach the second parameter with `removed` and `destroy=false`. Keep the generated `course-backend.tf` and `course-backend.hcl`.
5. Save, review and apply a plan for the refactor. Check that the renamed parameter keeps its AWS name/ID and the detached parameter still exists outside state.
6. Run `lab simulate-drift`. Make and apply a refresh-only plan to record the changed value. Clear refresh-only, then use a normal plan/apply to restore the desired value and tags.
7. Run `lab probe-locks`, make a fresh saved plan with detailed exit codes, then run `lab grade`. The probe holds its own `.tflock`, checks the real contention error, then releases only its matching lock.
8. Destroy the workload while S3 state is still available. Run `lab migrate-local`, preview with `lab recover`, then delete the detached owned parameter with `lab recover --execute`.
9. Destroy the backend bucket after migration, including its state versions and delete markers. Run `lab check-cleanup` once both workload and bootstrap resources are gone.

If a lock blocks you, check its owner; don't delete an active lock or backend bucket to get past it. You won't need DynamoDB. Recovery inventory leaves backend resources out by default to protect the state store.

Allow 55 minutes. Resources: one encrypted/versioned S3 bucket and settings, two standard SSM parameters, and temporary state/lock objects. Target cost: below $0.01 for a short run before credits. Requests and stored state versions can incur charges if left behind. Assumptions dated 2026-11-14.
