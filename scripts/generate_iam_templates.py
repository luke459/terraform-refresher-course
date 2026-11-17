"""Write reviewable per-lab permission templates; never attach policies."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]/'docs/iam'
ROOT.mkdir(exist_ok=True,parents=True)
ACCOUNT='${ACCOUNT_ID}'
REGION='${REGION}'
ATTEMPT='${ATTEMPT_ID}'
bucket=f'arn:aws:s3:::tf004-{ACCOUNT}-{ATTEMPT}-*'


def statement(sid,actions,resources='*',condition=None):
    result={'Sid':sid,'Effect':'Allow','Action':actions,'Resource':resources}
    if condition:result['Condition']=condition
    return result


services={
's3':[
    statement('DiscoverBuckets',['s3:ListAllMyBuckets']),
    statement('OwnedBucketLifecycle',['s3:CreateBucket','s3:DeleteBucket','s3:ListBucket','s3:ListBucketVersions','s3:GetBucket*','s3:PutBucketTagging','s3:DeleteBucketTagging','s3:PutBucketVersioning','s3:PutEncryptionConfiguration','s3:PutBucketPublicAccessBlock'],bucket),
    statement('OwnedObjectsAndLockfiles',['s3:GetObject','s3:GetObjectVersion','s3:PutObject','s3:DeleteObject','s3:DeleteObjectVersion'],bucket+'/*'),
],
'ssm':[
    statement('DiscoverParameters',['ssm:DescribeParameters']),
    statement('OwnedParameters',['ssm:GetParameter','ssm:GetParameters','ssm:PutParameter','ssm:DeleteParameter','ssm:AddTagsToResource','ssm:RemoveTagsFromResource','ssm:ListTagsForResource'],f'arn:aws:ssm:{REGION}:{ACCOUNT}:parameter/tf004/{ATTEMPT}/*'),
],
'ec2':[
    statement('ReadNetworking',['ec2:DescribeVpcs','ec2:DescribeVpcAttribute','ec2:DescribeSubnets','ec2:DescribeSecurityGroups','ec2:DescribeSecurityGroupRules','ec2:DescribeTags','ec2:DescribeNetworkAcls','ec2:DescribeRouteTables']),
    statement('CreateTaggedNetworking',['ec2:CreateVpc','ec2:CreateSubnet','ec2:CreateSecurityGroup'],[f'arn:aws:ec2:{REGION}:{ACCOUNT}:{kind}/*' for kind in ['vpc','subnet','security-group']],{'StringEquals':{'aws:RequestTag/Project':'tf-004-prep','aws:RequestTag/Attempt':ATTEMPT}}),
    statement('TagNetworkingDuringCreation',['ec2:CreateTags'],[f'arn:aws:ec2:{REGION}:{ACCOUNT}:{kind}/*' for kind in ['vpc','subnet','security-group','security-group-rule']],{'StringEquals':{'aws:RequestTag/Project':'tf-004-prep','aws:RequestTag/Attempt':ATTEMPT},'StringLike':{'ec2:CreateAction':['CreateVpc','CreateSubnet','CreateSecurityGroup','AuthorizeSecurityGroupIngress']}}),
    statement('UpdateExistingOwnedTags',['ec2:CreateTags','ec2:DeleteTags'],[f'arn:aws:ec2:{REGION}:{ACCOUNT}:{kind}/*' for kind in ['vpc','subnet','security-group','security-group-rule']],{'StringEquals':{'ec2:ResourceTag/Project':'tf-004-prep','ec2:ResourceTag/Attempt':ATTEMPT}}),
    statement('ManageOwnedNetworking',['ec2:DeleteVpc','ec2:ModifyVpcAttribute','ec2:DeleteSubnet','ec2:DeleteSecurityGroup','ec2:AuthorizeSecurityGroupIngress','ec2:AuthorizeSecurityGroupEgress','ec2:RevokeSecurityGroupIngress','ec2:RevokeSecurityGroupEgress'],[f'arn:aws:ec2:{REGION}:{ACCOUNT}:{kind}/*' for kind in ['vpc','subnet','security-group','security-group-rule']],{'StringEquals':{'ec2:ResourceTag/Project':'tf-004-prep','ec2:ResourceTag/Attempt':ATTEMPT}}),
],
'secretsmanager':[
    statement('DiscoverSecrets',['secretsmanager:ListSecrets']),
    statement('OwnedDisposableSecrets',['secretsmanager:CreateSecret','secretsmanager:DescribeSecret','secretsmanager:GetSecretValue','secretsmanager:PutSecretValue','secretsmanager:UpdateSecret','secretsmanager:DeleteSecret','secretsmanager:TagResource','secretsmanager:UntagResource','secretsmanager:ListSecretVersionIds','secretsmanager:UpdateSecretVersionStage'],f'arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:tf004-{ATTEMPT}-*'),
],
'iam':[
    statement('DiscoverLocalPolicies',['iam:ListPolicies']),
    statement('OwnedImportPolicy',['iam:CreatePolicy','iam:GetPolicy','iam:GetPolicyVersion','iam:ListPolicyVersions','iam:CreatePolicyVersion','iam:DeletePolicyVersion','iam:DeletePolicy','iam:TagPolicy','iam:UntagPolicy','iam:ListPolicyTags'],f'arn:aws:iam::{ACCOUNT}:policy/tf004-{ATTEMPT}-*'),
],
'sns':[
    statement('DiscoverTopics',['sns:ListTopics']),
    statement('OwnedTopic',['sns:CreateTopic','sns:GetTopicAttributes','sns:SetTopicAttributes','sns:DeleteTopic','sns:TagResource','sns:UntagResource','sns:ListTagsForResource'],f'arn:aws:sns:{REGION}:{ACCOUNT}:tf004-{ATTEMPT}-*'),
]}
domains={1:['s3','ssm'],2:['ssm'],3:['ec2'],4:['ec2','secretsmanager'],5:['ec2','ssm'],6:['s3','ssm'],7:['s3','iam'],8:['sns']}
for domain,names in domains.items():
    statements=[statement('CallerIdentity',['sts:GetCallerIdentity'])]
    for name in names:statements.extend(services[name])
    (ROOT/f'lab-{domain:02}.json').write_text(json.dumps({'Version':'2012-10-17','Statement':statements},indent=2)+'\n')
(ROOT/'lab-06-bootstrap.json').write_text(json.dumps({'Version':'2012-10-17','Statement':[statement('CallerIdentity',['sts:GetCallerIdentity']),*services['s3']]},indent=2)+'\n')
