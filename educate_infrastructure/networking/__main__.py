"""Manage the creation of VPC infrastructure and the peering relationships between them.


"""

import pulumi
from pulumi_aws import ec2, get_availability_zones, get_ami, GetAmiFilterArgs

from vpc import Vpc

vpc = Vpc()

pulumi.export("vpc_id", vpc.get_id())

size = "t2.micro"

ami = get_ami(
    most_recent=True,
    owners=["137112412989"],
    filters=[GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])],
)

group = ec2.SecurityGroup(
    "test-sg",
    vpc_id=vpc.get_id(),
    description="Enable HTTP access",
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        )
    ],
)

user_data = """
#!/bin/bash
echo "Hello, World!" > index.html
nohup python -m SimpleHTTPServer 80 &
"""

server = ec2.Instance(
    "test-ec2-instance",
    instance_type=size,
    subnet_id=vpc.get_public_subnet_id(),
    vpc_security_group_ids=[group.id],
    user_data=user_data,
    ami=ami.id,
)

pulumi.export("vpc_id", vpc.get_id())
pulumi.export("public_subnet_ids", vpc.get_public_subnet_id())
pulumi.export("public_ip", server.public_ip)
pulumi.export("public_dns", server.public_dns)

# TODO Create a VPC for the databases

# TODO Peer both VPCs