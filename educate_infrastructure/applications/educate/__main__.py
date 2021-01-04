""" Open edX native deployment on AWS"""

from pulumi import Config, get_stack, export, StackReference
from pulumi_aws import ebs, ec2, s3, get_ami, GetAmiFilterArgs, iam, lb, route53

from ec2 import DTEc2

env = get_stack()
networking_stack = StackReference(f"BbrSofiane/networking/prod")

apps_vpc_id = networking_stack.get_output("vpc_id")
apps_public_subnet_ids = networking_stack.get_output("public_subnet_ids")
apps_private_subnet_ids = networking_stack.get_output("public_private_ids")

# TODO Add resource dependencies opts=pulumi.ResourceOptions(depends_on=[server])

tags = {
    "Name": f"Educate App - {env}",
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
    f"educate-app-profile", role=educate_app_role.name
)

educate_app_instance = DTEc2(
    f"educate-app-{env}",
    apps_vpc_id,
    apps_private_subnet_ids[0],
    educate_app_profile.id,
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
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

# TODO Add enable_deletion_protection=True, access_logs
educate_app_alb = lb.LoadBalancer(
    f"educate-app-alb-{env}",
    load_balancer_type="application",
    security_groups=[sgroup.id],
    subnets=apps_public_subnet_ids,
    tags=tags,
)

educate_app_tg = lb.TargetGroup(
    f"educate-app-tg-{env}",
    port=80,
    protocol="HTTP",
    vpc_id=apps_vpc_id,
    tags=tags,
)

http_lb_listener = lb.Listener(
    f"educate-app-http-listener-{env}",
    load_balancer_arn=educate_app_alb.arn,
    port=80,
    default_actions=[
        lb.ListenerDefaultActionArgs(
            type="redirect",
            redirect=lb.ListenerDefaultActionRedirectArgs(
                port="443",
                protocol="HTTPS",
                status_code="HTTP_301",
            ),
        )
    ],
)

https_lb_listener = lb.Listener(
    f"educate-app-https-listener-{env}",
    load_balancer_arn=educate_app_alb.arn,
    port=443,
    protocol="HTTPS",
    ssl_policy="ELBSecurityPolicy-2016-08",
    certificate_arn="arn:aws:acm:eu-west-2:198538058567:certificate/4e597971-7430-44a7-b559-190c3ac7523d",
    default_actions=[{"type": "forward", "target_group_arn": educate_app_tg.arn}],
)

educate_target_group_attachment = lb.TargetGroupAttachment(
    f"educate-app-tg-attachement-{env}",
    target_group_arn=educate_app_tg.arn,
    target_id=educate_app_instance.get_instance_id(),
    port=80,
)

# TODO Move Route53 setup to its own project
# https://www.pulumi.com/docs/reference/pkg/aws/route53/record/#alias-record
zone = route53.get_zone(name="3ducate.co.uk")
records_required = DTEc2.get_required_records(env)
records = []

alias = route53.RecordAliasArgs(
    name=educate_app_alb.dns_name,
    zone_id=educate_app_alb.zone_id,
    evaluate_target_health=True,
)

if env == "prod":
    record_lms = route53.Record(
        f"educate-app-record-lms-{env}",
        zone_id=zone.zone_id,
        name=f"{zone.name}",
        type="A",
        aliases=[alias],
    )

    for record in records_required:
        add_record = route53.Record(
            f"educate-app-record-{record}-{env}",
            zone_id=zone.zone_id,
            name=f"{record}.{zone.name}",
            type="A",
            aliases=[alias],
        )
        records.append(add_record)
else:
    record_lms = route53.Record(
        f"educate-app-record-lms-{env}",
        zone_id=zone.zone_id,
        name=f"{env}.{zone.name}",
        type="A",
        aliases=[alias],
    )

    for record in records_required:
        add_record = route53.Record(
            f"educate-app-record-{record}-{env}",
            zone_id=zone.zone_id,
            name=f"{record}.{env}.{zone.name}",
            type="A",
            aliases=[alias],
        )
        records.append(add_record)
# record = route53.Record.get(resource_name="studio.prod.3ducate.co.uk", id="Z3IBKAQH9QPEYP_studio.prod.3ducate.co.uk_A")

export("instanceId", educate_app_instance.get_instance_id())
export("loadBalancerDnsName", educate_app_alb.dns_name)