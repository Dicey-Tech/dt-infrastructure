""" Open edX native deployment on AWS"""

from pulumi import Config, get_stack, export, StackReference
from pulumi_aws import ebs, ec2, s3, get_ami, GetAmiFilterArgs, iam

from ec2 import DTEc2

env = get_stack()
networking_stack = StackReference(f"BbrSofiane/networking/{env}")

apps_vpc_id = networking_stack.get_output("vpc_id")
apps_public_subnet_id = networking_stack.get_output("public_subnet_ids")
apps_private_subnet_id = networking_stack.get_output("public_private_ids")


# Create an IAM role for the open edx instance
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
    ]
)

educate_app_role = iam.Role(
    "educate-app-role", assume_role_policy=instance_assume_role_policy.json
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

public_app = DTEc2(
    "public-app", apps_vpc_id, apps_public_subnet_id, educate_app_profile.id
)
private_app = DTEc2(
    "private-app", apps_vpc_id, apps_private_subnet_id, educate_app_profile.id
)

export("publicIP", public_app.get_public_ip())
export("publicHostname", public_app.get_public_dns())

# config = Config("instance")

# openedx = DTEc2("test-ec2")

# export("publicIP", openedx.public_ip)
# export("publicHostname", openedx.public_dns)

# TODO Create a Load Balancer
"""
tags = {
    "Name": "Open edX Pulumi",
    "pulumi_managed": "true",
    "AutoOff": "True",
    "Owner": "Sofiane",
}

group = ec2.SecurityGroup(
    "openedx-pulumi-sg",
    description="Enable SSH and HTTP ACcess",
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
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=18000,
            to_port=18999,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags=tags,
)

with open("config.sh") as f:
    user_data = f.read()

openedx = ec2.Instance(
    "openedx-native",
    ami=config.require("ubuntu_2004"),
    instance_type=config.require("instance_type"),
    vpc_security_group_ids=[group.id],
    user_data=user_data,
    tags=tags,
    key_name=config.get("keyName"),
    root_block_device=ec2.InstanceRootBlockDeviceArgs(
        delete_on_termination=True, volume_size=50
    ),
)

export("publicIP", openedx.public_ip)
export("publicHostname", openedx.public_dns)

"""