"""Service-specific inventory and deletion, always scoped to an owned attempt."""
import json
import time
from botocore.exceptions import ClientError
from .terraform import state_resources


NOT_FOUND = {"NoSuchBucket", "NoSuchEntity", "NoSuchEntityException", "ParameterNotFound", "ResourceNotFoundException", "NotFound", "NotFoundException", "InvalidVpcID.NotFound", "InvalidSubnetID.NotFound", "InvalidGroup.NotFound", "InvalidSecurityGroupRuleId.NotFound"}
PRIMARY = {"aws_s3_bucket", "aws_ssm_parameter", "aws_vpc", "aws_subnet", "aws_security_group", "aws_vpc_security_group_ingress_rule", "aws_iam_policy", "aws_secretsmanager_secret", "aws_sns_topic"}
COMPANIONS = {"aws_s3_bucket_versioning", "aws_s3_bucket_server_side_encryption_configuration", "aws_s3_bucket_public_access_block", "aws_secretsmanager_secret_version"}


class ResourceInventory:
    def __init__(self, db, credentials):
        self.db, self.credentials = db, credentials

    def capture(self, attempt, state, prefix=""):
        for resource in state_resources(state):
            if resource.get("mode") != "managed":
                continue
            kind = resource["type"]
            if kind in COMPANIONS:
                continue
            if kind not in PRIMARY:
                raise ValueError(f"No cleanup adapter exists for {kind}; remove it from the lab before proceeding")
            values = resource.get("values", {})
            resource_id = values.get("id")
            if not resource_id:
                raise ValueError(f"Resource {resource['address']} has no inspectable ID")
            tags = values.get("tags_all") or values.get("tags") or {}
            arn = values.get("arn")
            region = arn.split(":")[3] if arn and len(arn.split(":")) > 3 else ""
            if kind == "aws_iam_policy":
                region = "global"
            if not region:
                region = "eu-west-2" if tags.get("RegionRole") == "uk" else "us-east-1" if attempt['domain_id']=='02' else attempt["region"]
            self.register(attempt, prefix + resource["address"], kind, resource_id, region, arn, tags)

    def register(self, attempt, address, kind, resource_id, region, arn=None, tags=None):
        self.db.execute("""INSERT INTO resources(attempt_id,address,type,resource_id,region,arn,tags)
            VALUES (?,?,?,?,?,?,?) ON CONFLICT(attempt_id,address,resource_id) DO UPDATE SET
            region=excluded.region,arn=excluded.arn,tags=excluded.tags,status='present'""",
            (attempt["id"], address, kind, resource_id, region, arn, json.dumps(tags or {})))

    def rows(self, attempt_id):
        return self.db.all("SELECT * FROM resources WHERE attempt_id=?", (attempt_id,))

    def reconcile(self, attempt):
        """Discover tagged leftovers by exact attempt identity, never by Project alone."""
        required={'Project':'tf-004-prep','ManagedBy':'terraform','Lab':attempt['domain_id'],'Attempt':attempt['id']}
        known={row['resource_id'] for row in self.rows(attempt['id'])}
        found=[]
        def add(kind,rid,region,arn=None,tags=None,address=None):
            if rid in known:
                return
            candidate={'type':kind,'resource_id':rid,'region':region}
            if tags is None:
                observed=self.inspect(candidate)
                if not observed['exists']:
                    return
                tags=observed['tags']
            if not all(tags.get(key)==value for key,value in required.items()):
                return
            address=address or f'orphan.{kind}.{rid}'
            self.register(attempt,address,kind,rid,region,arn,tags)
            self.db.execute('UPDATE resources SET ownership_verified=1 WHERE attempt_id=? AND address=? AND resource_id=?',(attempt['id'],address,rid))
            known.add(rid);found.append(rid)
        domain=attempt['domain_id']
        regions=['us-east-1','eu-west-2'] if domain=='02' else [attempt['region']]
        for region in regions:
            if domain in {'01','02','05','06'}:
                ssm=self.credentials.client('ssm',region)
                for page in ssm.get_paginator('describe_parameters').paginate(ParameterFilters=[{'Key':'Name','Option':'BeginsWith','Values':[f"/tf004/{attempt['id']}/"]}]):
                    for parameter in page.get('Parameters',[]):
                        add('aws_ssm_parameter',parameter['Name'],region)
            if domain in {'03','04','05'}:
                ec2=self.credentials.client('ec2',region)
                filters=[{'Name':'tag:'+key,'Values':[value]} for key,value in required.items()]
                for operation,key,kind,id_key in [('describe_vpcs','Vpcs','aws_vpc','VpcId'),('describe_subnets','Subnets','aws_subnet','SubnetId'),('describe_security_groups','SecurityGroups','aws_security_group','GroupId')]:
                    for page in ec2.get_paginator(operation).paginate(Filters=filters):
                        for resource in page.get(key,[]):
                            add(kind,resource[id_key],region,tags=self.tags(resource.get('Tags',[])))
            if domain=='04':
                secrets=self.credentials.client('secretsmanager',region)
                for page in secrets.get_paginator('list_secrets').paginate(Filters=[{'Key':'name','Values':[f"tf004-{attempt['id']}-"]}],IncludePlannedDeletion=True):
                    for secret in page.get('SecretList',[]):
                        add('aws_secretsmanager_secret',secret['ARN'],region,secret['ARN'],self.tags(secret.get('Tags',[])))
            if domain=='08':
                sns=self.credentials.client('sns',region)
                for page in sns.get_paginator('list_topics').paginate():
                    for topic in page.get('Topics',[]):
                        if f":tf004-{attempt['id']}-" in topic['TopicArn']:
                            add('aws_sns_topic',topic['TopicArn'],region,topic['TopicArn'])
        if domain in {'01','06','07'}:
            s3=self.credentials.client('s3',attempt['region'])
            pages=s3.get_paginator('list_buckets').paginate() if s3.can_paginate('list_buckets') else [s3.list_buckets()]
            prefix=f"tf004-{attempt['account']}-{attempt['id']}-"
            for page in pages:
                for bucket in page.get('Buckets',[]):
                    name=bucket['Name']
                    if name.startswith(prefix):
                        address='bootstrap.aws_s3_bucket.state' if name.endswith('-state') else None
                        add('aws_s3_bucket',name,attempt['region'],f'arn:aws:s3:::{name}',address=address)
        if domain=='07':
            iam=self.credentials.client('iam','us-east-1')
            name=f"tf004-{attempt['id']}-import"
            for page in iam.get_paginator('list_policies').paginate(Scope='Local'):
                for policy in page.get('Policies',[]):
                    if policy['PolicyName']==name:
                        add('aws_iam_policy',policy['Arn'],'global',policy['Arn'])
        return {'reconciled_resources':len(found)}

    @staticmethod
    def tags(items):
        return {item["Key"]: item["Value"] for item in items}

    def inspect(self, resource):
        kind, rid, region = resource["type"], resource["resource_id"], resource["region"]
        client = self.credentials.client
        try:
            if kind == "aws_s3_bucket":
                s3 = client("s3", region)
                s3.head_bucket(Bucket=rid)
                try:
                    tags = self.tags(s3.get_bucket_tagging(Bucket=rid).get("TagSet", []))
                except ClientError as exc:
                    if exc.response["Error"]["Code"] != "NoSuchTagSet":
                        raise
                    tags = {}
            elif kind == "aws_ssm_parameter":
                ssm = client("ssm", region)
                ssm.get_parameter(Name=rid)
                tags = self.tags(ssm.list_tags_for_resource(ResourceType="Parameter", ResourceId=rid).get("TagList", []))
            elif kind in {"aws_vpc", "aws_subnet", "aws_security_group", "aws_vpc_security_group_ingress_rule"}:
                method, argument, response_key = {
                    "aws_vpc": ("describe_vpcs", "VpcIds", "Vpcs"),
                    "aws_subnet": ("describe_subnets", "SubnetIds", "Subnets"),
                    "aws_security_group": ("describe_security_groups", "GroupIds", "SecurityGroups"),
                    "aws_vpc_security_group_ingress_rule": ("describe_security_group_rules", "SecurityGroupRuleIds", "SecurityGroupRules"),
                }[kind]
                found = getattr(client("ec2", region), method)(**{argument: [rid]})[response_key]
                if not found:
                    return {"exists": False, "tags": {}}
                tags = self.tags(found[0].get("Tags", []))
            elif kind == "aws_iam_policy":
                iam = client("iam", "us-east-1")
                iam.get_policy(PolicyArn=rid)
                tags = self.tags(iam.list_policy_tags(PolicyArn=rid).get("Tags", []))
            elif kind == "aws_secretsmanager_secret":
                found = client("secretsmanager", region).describe_secret(SecretId=rid)
                tags = self.tags(found.get("Tags", []))
            elif kind == "aws_sns_topic":
                sns = client("sns", region)
                sns.get_topic_attributes(TopicArn=rid)
                tags = self.tags(sns.list_tags_for_resource(ResourceArn=rid).get("Tags", []))
            else:
                raise ValueError(f"Unsupported resource adapter: {kind}")
            return {"exists": True, "tags": tags}
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in NOT_FOUND or (kind == "aws_s3_bucket" and code == "404"):
                return {"exists": False, "tags": {}}
            raise

    def verify_owned(self, attempt, expected_ids=None):
        resources = self.rows(attempt["id"])
        if not resources:
            raise ValueError("No inventoried cloud resources exist for this attempt")
        live = 0
        for resource in resources:
            found = self.inspect(resource)
            if not found["exists"]:
                if expected_ids is not None and resource['resource_id'] in expected_ids:
                    raise ValueError(f"Expected resource is absent: {resource['address']}")
                self.db.execute("UPDATE resources SET status='absent' WHERE attempt_id=? AND address=? AND resource_id=?",
                    (attempt['id'],resource['address'],resource['resource_id']))
                continue
            required = {"Project": "tf-004-prep", "ManagedBy": "terraform", "Attempt": attempt["id"], "Lab": attempt["domain_id"]}
            if any(found["tags"].get(key) != value for key, value in required.items()):
                raise ValueError(f"Ownership tags do not match: {resource['address']}")
            self.db.execute("UPDATE resources SET ownership_verified=1 WHERE attempt_id=? AND address=? AND resource_id=?",
                (attempt["id"], resource["address"], resource["resource_id"]))
            live += 1
        if live == 0:
            raise ValueError('No inventoried resources remain live for ownership verification')
        return {"verified_resources": live}

    def absence(self, attempt, resources=None):
        remaining = []
        for resource in self.rows(attempt["id"]) if resources is None else resources:
            found = self.inspect(resource)
            if found["exists"]:
                remaining.append(resource["address"])
            else:
                self.db.execute("UPDATE resources SET status='absent' WHERE attempt_id=? AND address=? AND resource_id=?",
                    (attempt["id"], resource["address"], resource["resource_id"]))
        return remaining

    def delete(self, attempt, resource):
        self.credentials.verify(attempt["account"])
        found = self.inspect(resource)
        if not found["exists"]:
            return
        tags = found["tags"]
        required = {"Project": "tf-004-prep", "ManagedBy": "terraform", "Attempt": attempt["id"], "Lab": attempt["domain_id"]}
        if not all(tags.get(key) == value for key, value in required.items()):
            # A removed tag may be recovered only after ownership was previously verified live.
            if not resource["ownership_verified"] or any(key in tags and tags[key] != value for key, value in required.items()):
                raise ValueError(f"Refusing deletion: ownership cannot be established for {resource['address']}")
        kind, rid, region = resource["type"], resource["resource_id"], resource["region"]
        client = self.credentials.client
        if kind == "aws_s3_bucket":
            s3 = client("s3", region)
            for page in s3.get_paginator("list_object_versions").paginate(Bucket=rid):
                objects = [{"Key": obj["Key"], "VersionId": obj["VersionId"]} for key in ("Versions", "DeleteMarkers") for obj in page.get(key, [])]
                if objects:
                    result = s3.delete_objects(Bucket=rid, Delete={"Objects": objects, "Quiet": True})
                    if result.get("Errors"):
                        raise ValueError("S3 version deletion was incomplete")
            for page in s3.get_paginator("list_objects_v2").paginate(Bucket=rid):
                objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
                if objects:
                    result = s3.delete_objects(Bucket=rid, Delete={"Objects": objects, "Quiet": True})
                    if result.get("Errors"):
                        raise ValueError("S3 object deletion was incomplete")
            s3.delete_bucket(Bucket=rid)
        elif kind == "aws_ssm_parameter":
            client("ssm", region).delete_parameter(Name=rid)
        elif kind == "aws_iam_policy":
            iam = client("iam", "us-east-1")
            for page in iam.get_paginator("list_policy_versions").paginate(PolicyArn=rid):
                for version in page["Versions"]:
                    if not version["IsDefaultVersion"]:
                        iam.delete_policy_version(PolicyArn=rid, VersionId=version["VersionId"])
            iam.delete_policy(PolicyArn=rid)
        elif kind == "aws_secretsmanager_secret":
            client("secretsmanager", region).delete_secret(SecretId=rid, ForceDeleteWithoutRecovery=True)
        elif kind == "aws_sns_topic":
            client("sns", region).delete_topic(TopicArn=rid)
        elif kind == "aws_vpc_security_group_ingress_rule":
            ec2 = client("ec2", region)
            rule = ec2.describe_security_group_rules(SecurityGroupRuleIds=[rid])["SecurityGroupRules"][0]
            ec2.revoke_security_group_ingress(GroupId=rule["GroupId"], SecurityGroupRuleIds=[rid])
        elif kind == "aws_security_group":
            client("ec2", region).delete_security_group(GroupId=rid)
        elif kind == "aws_subnet":
            client("ec2", region).delete_subnet(SubnetId=rid)
        elif kind == "aws_vpc":
            client("ec2", region).delete_vpc(VpcId=rid)
        else:
            raise ValueError(f"No deletion adapter for {kind}")

    def reap(self, attempt, execute=False):
        self.reconcile(attempt)
        order = {"aws_vpc_security_group_ingress_rule": 0, "aws_security_group": 1, "aws_subnet": 2, "aws_vpc": 3}
        rows = sorted([row for row in self.rows(attempt["id"]) if not row['address'].startswith('bootstrap.')], key=lambda r: order.get(r["type"], 0))
        report = [{"address": r["address"], "id": r["resource_id"], "region": r["region"], **self.inspect(r)} for r in rows]
        if execute:
            for resource in rows:
                self.delete(attempt, resource)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if not self.absence(attempt, rows):
                    return {"executed": True, "scope":"workload; bootstrap excluded", "resources": report, "remaining": []}
                time.sleep(2)
            raise ValueError("Deletion is still pending. Retry the cleanup check; completion was not awarded.")
        return {"executed": False, "account": attempt["account"], "attempt": attempt["id"], "resources": report}

