# Lab 03: review, apply and replace safely

Your first task is to fix the subnet CIDR and formatting in the VPC, subnet and security group starter. Use `10.43.1.0/24` inside the `10.43.0.0/16` VPC. Keep the ownership tags and the security group address `aws_security_group.app`.

1. Fix the CIDR, then initialize, format and validate from the terminal.
2. Save a plan as `tfplan`, read the proposed changes, then apply it.
3. Run `lab capture-baseline` so you can compare the security group's ID later.
4. Run `lab simulate-drift`. It adds a TCP 8443 ingress rule from `10.43.0.0/16` to this attempt's empty security group. No compute is attached.
5. Create a saved replacement plan for `aws_security_group.app`. Review the proposed replacement, then apply that plan. Leave the replacement flag off later plans.
6. Make a fresh saved plan with detailed exit codes, then run `lab grade`. The checks confirm formatting, the saved plan and apply, the replacement operation, and a new security group ID.
7. Destroy the resources and run `lab check-cleanup` to finish.

Use `-replace` for this exercise; `taint` or `state rm` won't demonstrate the intended workflow. You don't need an EC2 instance. If you need a reminder of the replacement syntax, revisit the lesson or type `help`.

Allow 40 minutes. Resources: one VPC, one subnet and one security group; replacement briefly overlaps two owned security groups. No NAT, instances, endpoints or public IPs. Target cost: below $0.01 in any supported region before credits, using this setup. Assumptions dated 2026-11-14. Clean up even when the lab has no hourly compute charges.
