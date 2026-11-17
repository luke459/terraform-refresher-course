# Lab 04: contracts and a password that is not persisted

Build one security group per service using the typed services map. Validate CIDR and port syntax, block public SSH with a precondition, require the expected VPC with a postcondition, and verify deployed service count with a top-level check. Generate the password through an ephemeral random_password and deliver it to Secrets Manager through secret_string_wo plus its version counter.

The starter intentionally opens SSH to 0.0.0.0/0. Change that CIDR to the private lab subnet 10.44.1.0/24. Keep the VPC and ownership values supplied by the workspace. Read the solution only after tracing why the precondition blocks the starter's plan.

1. Run Init, Format and Validate config. The frozen providers must support ephemeral passwords and the write-only secret field.
2. Observe the public-SSH precondition failure before fixing the CIDR. Invalid port/CIDR values must also fail the input contract.
3. Fix the configuration, then Plan and Apply saved plan. All conditions and checks must evaluate successfully.
4. Run another Plan, then Grade lab. It must show zero managed-resource and root-output changes. On Terraform 1.12, a scoped check data source can still be scheduled for a read, giving detailed exit code 2 despite zero managed changes; the grader inspects the structured plan. The validator also reads the actual live secret into memory, compares it against real state/plan representations and retained workspace files, and never prints it.
5. Inspect the State Leak Inspector examples: sensitive redaction alone does not satisfy non-persistence. Do not add an output that exposes the password.
6. Destroy and Verify cleanup. The parent secret has a zero-day recovery window because it is disposable; AWS deletion may still take time. Retry the cleanup check until absence is confirmed.

To rotate an intentionally changed write-only value, increment secret_version; Terraform cannot compare the old write-only value in state. Do not put AWS access keys into HCL. Vault concepts are covered in the lesson without requiring a Vault service.

Allow 50 minutes. Resources: one VPC, two security groups, one ephemeral password, one Secrets Manager secret/version. Target gross cost below $0.01 for a short session in any supported course region, with no replicas or rotation service; Secrets Manager storage and API requests are billable. No free-tier guarantee. Assumptions dated 2026-11-14.
