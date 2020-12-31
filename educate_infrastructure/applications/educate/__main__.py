""" Open edX native deployment on AWS"""

from pulumi import Config, get_stack, export, StackReference
from pulumi_aws import ebs, ec2, s3, get_ami, GetAmiFilterArgs, iam, lb, route53

from ec2 import DTEc2

env = get_stack()
networking_stack = StackReference(f"BbrSofiane/networking/{env}")

apps_vpc_id = networking_stack.get_output("vpc_id")
apps_public_subnet_ids = networking_stack.get_output("public_subnet_ids")
apps_private_subnet_ids = networking_stack.get_output("public_private_ids")

tags = {
    "Name": "Educate App",
    "pulumi_managed": "true",
}

# Create an IAM role for the open edx instance
# TODO Create abstraction for IAM role
instance_assume_role_policy = iam.get_policy_document(
    statements=[
        iam.GetPolicyDocumentStatementArgs(
            actions=["sts:AssumeRole"],
            principals=[
                iam.GetPolicyDocumentStatementPrincipalArgs(
                    type="Service",
                    identifiers=["ec2.amazonaws.com"],
                )
            ],
        )
    ],
)

educate_app_role = iam.Role(
    "educate-app-role", assume_role_policy=instance_assume_role_policy.json, tags=tags
)

ssm_role_policy_attach = iam.RolePolicyAttachment(
    "ssm-educate-app-policy-attach",
    role=educate_app_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
)

s3_role_policy_attach = iam.RolePolicyAttachment(
    "s3-educate-app-policy-attach",
    role=educate_app_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
)

educate_app_profile = iam.InstanceProfile(
    "educate-app-profile", role=educate_app_role.name
)


educate_app_instance = DTEc2(
    "educate-app", apps_vpc_id, apps_public_subnet_ids[0], educate_app_profile.id
)

# TODO Create a load balancer to listen for HTTP traffic on port 80 and 443.
sgroup = ec2.SecurityGroup(
    f"educate-app-alb-sg",
    vpc_id=apps_vpc_id,
    description="Enable HTTP access",
    egress=[
        ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

# TODO Add enable_deletion_protection=True, access_logs
educate_app_alb = lb.LoadBalancer(
    "educate-app-alb",
    load_balancer_type="application",
    security_groups=[sgroup.id],
    subnets=apps_public_subnet_ids,
    tags=tags,
)

educate_app_tg = lb.TargetGroup(
    "educate-app-tg",
    port=80,
    protocol="HTTP",
    vpc_id=apps_vpc_id,
    tags=tags,
)

lb_listener = lb.Listener(
    "educate-app-listener",
    load_balancer_arn=educate_app_alb.arn,
    port=80,
    default_actions=[{"type": "forward", "target_group_arn": educate_app_tg.arn}],
)

educate_target_group_attachment = lb.TargetGroupAttachment(
    "educate-app-tg-attachement",
    target_group_arn=educate_app_tg.arn,
    target_id=educate_app_instance.get_instance_id(),
    port=80,
)

# TODO Move Route53 setup to its own project
# https://www.pulumi.com/docs/reference/pkg/aws/route53/record/#alias-record
zone = route53.get_zone(name="3ducate.co.uk")
alias = route53.RecordAliasArgs(
        name=educate_app_alb.dns_name,
        zone_id=educate_app_alb.zone_id,
        evaluate_target_health=True,
    )

record = route53.Record(
    "educate-app-record",
    zone_id=zone.zone_id,
    name=f"studio.prod.{zone.name}",
    type="A",
    aliases=[alias]
)
# record = route53.Record.get(resource_name="studio.prod.3ducate.co.uk", id="Z3IBKAQH9QPEYP_studio.prod.3ducate.co.uk_A") 

export("instanceId", educate_app_instance.get_instance_id())
export("loadBalancerDnsName", educate_app_alb.dns_name)