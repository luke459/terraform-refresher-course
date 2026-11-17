# Lab 06: move state and preserve resource identity

Begin with the starter's legacy and detached SSM parameters in local state. The bootstrap directory independently manages an encrypted, versioned S3 bucket. Migrate the workload to that bucket using native lockfiles, rename the legacy resource with moved, and remove the detached resource from state without destroying it.

1. Init, Plan and Apply the starter workload. Capture resource IDs before changing resource addresses.
2. Under State backend workflow, initialize, plan and apply the bootstrap bucket. It has separate local state.
3. Migrate workload state to S3. The runner writes a partial backend configuration with use_lockfile=true and encrypt=true, without embedding credentials.
4. Replace the root main.tf with the reference refactor: legacy becomes metadata through moved; removed with destroy=false detaches the second parameter. Keep the generated course-backend.tf and course-backend.hcl.
5. Plan and apply the refactor. The renamed parameter must retain its original AWS name/ID, and the detached parameter must still exist outside state.
6. Simulate owned-resource drift. Make and apply a refresh-only plan to observe the new value in state; clear refresh-only and run a normal plan/apply to restore desired value and tags.
7. Run the native lock probe, then a no-change Plan and Grade lab. The probe deliberately holds an owned .tflock while a real Terraform plan attempts to acquire it, checks the contention error, then releases only that probe lock.
8. Destroy the workload while its S3 backend still exists. Migrate its empty state back to local. Preview recovery inventory and delete the detached owned parameter.
9. Destroy the bootstrap bucket only after local migration. Its versioned state objects and delete markers must be removed. Verify cleanup after both workload and bootstrap resources are absent.

Do not delete an active lock or its backend bucket to bypass contention. Do not create a DynamoDB table. Recovery inventory excludes backend resources by default to protect state storage.

Allow 55 minutes. Resources: one encrypted/versioned S3 bucket and settings, two standard SSM parameters and transient state/lock objects. Gross target below $0.01 for a short run in either region, before credits. Request and state-version storage charges can accrue if left behind. Assumptions dated 2026-11-14.
