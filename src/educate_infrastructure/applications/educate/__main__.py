""" Open edX native deployment on AWS"""

from pulumi import Config, get_stack, get_project, export, StackReference
from pulumi_aws import ec2, iam, lb, route53

from educate_infrastructure.applications.educate.ec2 import DTEc2, DTEducateConfig

env = get_stack()
proj = get_project()

networking_stack = StackReference("BbrSofiane/networking/prod")

apps_vpc_id = networking_stack.get_output("apps_vpc_id")
apps_public_subnet_ids = networking_stack.get_output("apps_public_subnet_ids")
apps_private_subnet_ids = networking_stack.get_output("apps_private_subnet_ids")

# TODO Add resource dependencies opts=pulumi.ResourceOptions(depends_on=[server])

tags = {
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
    f"{proj}-role", assume_role_policy=instance_assume_role_policy.json, tags=tags
)

ssm_role_policy_attach = iam.RolePolicyAttachment(
    f"ssm-{proj}-policy-attach",
    role=educate_app_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
)

s3_role_policy_attach = iam.RolePolicyAttachment(
    f"s3-{proj}-policy-attach",
    role=educate_app_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
)

educate_app_profile = iam.InstanceProfile(f"{proj}-profile", role=educate_app_role.name)

security_group = ec2.SecurityGroup(
    f"{proj}-{env}-sg",
    vpc_id=apps_vpc_id,
    description="Enable HTTP and HTTPS access",
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
            protocol=ec2.ProtocolType.TCP,
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol=ec2.ProtocolType.TCP,
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol=ec2.ProtocolType.TCP,
            from_port=18000,
            to_port=18999,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags={**tags, "Name": "Educate Security Group"},
)

instance_config = DTEducateConfig(
    name=f"{proj}-{env}",
    app_vpc_id=apps_vpc_id,
    app_subnet_id=apps_private_subnet_ids[0],
    iam_instance_profile_id=educate_app_profile.id,
    security_group_id=security_group.id,
    instance_type=ec2.InstanceType.T3A_LARGE,
)

educate_app_instance = DTEc2(instance_config)

# TODO Add enable_deletion_protection=True, access_logs
educate_app_alb = lb.LoadBalancer(
    f"{proj}-alb-{env}",
    load_balancer_type="application",
    security_groups=[security_group.id],
    subnets=apps_public_subnet_ids,
    tags=tags,
)

educate_app_tg = lb.TargetGroup(
    f"{proj}-tg-{env}",
    port=80,
    protocol="HTTP",
    vpc_id=apps_vpc_id,
    tags=tags,
)

http_lb_listener = lb.Listener(
    f"{proj}-http-listener-{env}",
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
    f"{proj}-https-listener-{env}",
    load_balancer_arn=educate_app_alb.arn,
    port=443,
    protocol="HTTPS",
    ssl_policy="ELBSecurityPolicy-2016-08",
    certificate_arn="arn:aws:acm:eu-west-2:198538058567:certificate/4e597971-7430-44a7-b559-190c3ac7523d",
    default_actions=[{"type": "forward", "target_group_arn": educate_app_tg.arn}],
)

educate_target_group_attachment = lb.TargetGroupAttachment(
    f"{proj}-tg-attachement-{env}",
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
        f"{proj}-record-lms-{env}",
        zone_id=zone.zone_id,
        name=f"{zone.name}",
        type="A",
        aliases=[alias],
    )

    for record in records_required:
        add_record = route53.Record(
            f"{proj}-record-{record}-{env}",
            zone_id=zone.zone_id,
            name=f"{record}.{zone.name}",
            type="A",
            aliases=[alias],
        )
        records.append(add_record)
else:
    record_lms = route53.Record(
        f"{proj}-record-lms-{env}",
        zone_id=zone.zone_id,
        name=f"{env}.{zone.name}",
        type="A",
        aliases=[alias],
    )

    for record in records_required:
        add_record = route53.Record(
            f"{proj}-record-{record}-{env}",
            zone_id=zone.zone_id,
            name=f"{record}.{env}.{zone.name}",
            type="A",
            aliases=[alias],
        )
        records.append(add_record)

export("instanceId", educate_app_instance.get_instance_id())
export("loadBalancerDnsName", educate_app_alb.dns_name)
export("fullDomainName", record_lms.fqdn)
