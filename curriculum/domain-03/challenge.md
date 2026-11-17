# Lab 03: review, apply, and replace safely

Repair the deliberately invalid subnet CIDR and formatting in the VPC/subnet/security-group starter. Use 10.43.1.0/24 inside the declared 10.43.0.0/16 VPC. Keep ownership tags and the disposable security group address aws_security_group.app.

1. Start the lab, fix the CIDR, then run Init, Format and Validate config.
2. Plan and review the saved plan, then Apply saved plan.
3. Use Capture resource IDs to record the initial security group identity.
4. Use Simulate owned-resource drift to add an out-of-band TCP 8443 ingress rule from the private lab CIDR 10.43.0.0/16. The empty security group is owned by this attempt and has no attached compute.
5. In Plan and debug options, enter aws_security_group.app as the replacement address. Plan and review the replacement, then apply the saved plan. Clear the replacement option afterward.
6. Run a no-change Plan and Grade lab. The grader requires formatting, saved-plan/apply receipts, a recorded replacement operation, and a changed security group ID.
7. Destroy the lab resources and Verify cleanup.

Do not use taint or state rm as a replacement shortcut. No EC2 instance is needed to demonstrate -replace. CLI equivalent: tfprep run 03 --replace aws_security_group.app -- plan.

Allow 40 minutes. Resources: one VPC, one subnet and one security group; replacement temporarily overlaps two owned security groups. No NAT, instances, endpoints or public IPs. Target gross cost below $0.01 in any supported course region for this topology, before credits; pricing assumptions dated 2026-11-14. Teardown remains mandatory even when no hourly compute is involved.
