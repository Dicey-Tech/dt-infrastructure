"""An AWS Python Pulumi program"""

import pulumi
from pulumi_aws import ec2, get_availability_zones, get_ami, GetAmiFilterArgs

# from vpc import Vpc

config = pulumi.Config()
az_count = config.require_int("az_count")

tags = {"pulumi_managed": "true", "AutoOff": "True"}

zones = get_availability_zones().names[:az_count]

# TODO Create a VPC for the apps
vpc = ec2.Vpc("educate-app-vpc", cidr_block="10.0.0.0/16")

igw = ec2.InternetGateway("educate-app-igw", vpc_id=vpc.id)

public_route_table = ec2.RouteTable(
    "educate-app-rt",
    routes=[ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=igw.id)],
    vpc_id=vpc.id,
)

public_subnet_ids = []

for zone in zones:
    # TODO Create 1 public and 1 private subnet
    public_subnet = ec2.Subnet(
        f"educate-public-subnet-{zone}",
        assign_ipv6_address_on_creation=False,
        vpc_id=vpc.id,
        map_public_ip_on_launch=True,
        cidr_block="10.0.1.0/24",
        availability_zone=zone,
        tags=tags,
    )

    ec2.RouteTableAssociation(
        f"educate-app-public-rta-{zone}",
        route_table_id=public_route_table.id,
        subnet_id=public_subnet.id,
    )

    public_subnet_ids.append(public_subnet.id)


pulumi.export("vpc_id", vpc.id)

size = "t2.micro"

ami = get_ami(
    most_recent=True,
    owners=["137112412989"],
    filters=[GetAmiFilterArgs(name="name", values=["amzn-ami-hvm-*"])],
)

group = ec2.SecurityGroup(
    "test-sg",
    vpc_id=vpc.id,
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
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[group.id],
    user_data=user_data,
    ami=ami.id,
)

pulumi.export("vpc_id", vpc.id)
pulumi.export("public_subnet_ids", public_subnet_ids)
pulumi.export("public_ip", server.public_ip)
pulumi.export("public_dns", server.public_dns)

# TODO Create a VPC for the databases

# TODO Peer both VPCs