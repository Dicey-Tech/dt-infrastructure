"""Manage the creation of an RDS instance
and a MongoDB instance deployed in an EC2 instance.


"""
from pulumi import Config, get_stack, export, get_project, StackReference
from pulumi_aws import ec2

from educate_infrastructure.lib.dt_types import AWSBase
from educate_infrastructure.databases.database import DTAuroraConfig, DTAuroraCluster
from educate_infrastructure.databases.mongodb import DTMongoDBConfig, DTMongoDB


env = get_stack()
proj = get_project()

network_stack = StackReference("BbrSofiane/networking/prod")

snapshot = Config("sql").get("snapshot")

db_vpc_id = network_stack.get_output("apps_vpc_id")
db_private_subnet_ids = network_stack.get_output("apps_private_subnet_ids")
db_subnet_group_name = network_stack.get_output("db_subnet_group_name")

mysql_db_sg = ec2.SecurityGroup(
    f"mysql-db-sg-{env}",
    description="Access from the database VPC to the MySQL database",
    ingress=[
        ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=3306,
            to_port=3306,
            cidr_blocks=["0.0.0.0/0"],
            description="MySQL access from Educate App instances",
        ),
    ],
    vpc_id=db_vpc_id,
)

aurora_cluster_config = DTAuroraConfig(
    instance_name=f"educate-sql-db-{env}",
    subnet_group_name=db_subnet_group_name,
    # password="password",
    security_groups=[mysql_db_sg],
    tags={"pulumi_managed": "True"},
    snapshot_identifier=snapshot,
    prevent_delete=False,  # For testing
    multi_az=False,
)

aurora_cluster = DTAuroraCluster(db_config=aurora_cluster_config)

# TODO Provision MongoDB Instance
mongodb_config = DTMongoDBConfig(
    name=f"educate-mongodb-{env}",
    vpc_id=db_vpc_id,
    subnet_id=db_private_subnet_ids[0],
    instance_type=ec2.InstanceType.T3A_MICRO,
)

mongodb_cluster = DTMongoDB(mongodb_config)

export("mongodb_endpoint", mongodb_cluster.get_private_dns())
export("mysql_endpoint", aurora_cluster.get_endpoint())
