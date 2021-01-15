""" RDS """
from enum import Enum
from typing import Dict, List, Optional, Text, Union

from pulumi import ComponentResource, Output
from pulumi_aws import rds
from pulumi_aws.ec2 import SecurityGroup
from pydantic import BaseModel, PositiveInt, SecretStr, conint

# from educate_infrastructure.lib.dt_types import AWSBase

MAX_BACKUP_DAYS = 35


# TODO Remove
class AWSBase(BaseModel):
    """Base class for deriving configuration objects to pass to AWS component resources."""

    tags: Dict
    region: Text = "eu-west-2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tags.update({"pulumi_managed": "true"})


class DTReplicaDBConfig(BaseModel):
    """Configuration object for defining configuration needed to create a read replica."""

    instance_size: Text = rds.InstanceType.T3_MEDIUM
    storage_type: rds.StorageType = rds.StorageType.GP2
    public_access: bool = False
    security_groups: Optional[List[SecurityGroup]] = None

    class Config:
        arbitrary_types_allowed = True


class DTRDSConfig(AWSBase):
    """Configuration object for defining the interface to create an RDS instance with sane defaults."""

    engine: Text
    engine_version: Text
    instance_name: Text  # The name of the RDS instance
    password: SecretStr
    # parameter_overrides: List[Dict[Text, Union[Text, bool, int, float]]]  # noqa: WPS234
    port: PositiveInt
    subnet_group_name: Union[Text, Output[str]]
    security_groups: List[SecurityGroup]
    backup_days: conint(ge=0, le=MAX_BACKUP_DAYS, strict=True) = 30  # type: ignore
    db_name: Optional[Text] = None  # The name of the database schema to create
    instance_size: Text = "db.t2.large"
    is_public: bool = False
    max_storage: Optional[PositiveInt] = None  # Set to allow for storage autoscaling
    multi_az: bool = True
    prevent_delete: bool = True
    public_access: bool = False
    take_final_snapshot: bool = True
    storage: PositiveInt = PositiveInt(50)  # noqa: WPS432
    storage_type: rds.StorageType = rds.StorageType.GP2
    username: Text = "dtdevops"
    read_replica: Optional[DTReplicaDBConfig] = None

    class Config:
        arbitrary_types_allowed = True


class DTMySQLConfig(DTRDSConfig):
    """Configuration container to specify settings specific to MySQL."""

    engine: Text = "mysql"
    engine_version: Text = "5.7"
    port: PositiveInt = PositiveInt(3306)
    instance_size: Text = rds.InstanceType.T3_LARGE
    snapshot_identifier: Optional[Text]
    family: Text = "mysql5.7"


class DTAuroraConfig(DTRDSConfig):
    """Configuration container to specify settings specific to Aurora."""

    engine: Text = rds.EngineType.AURORA_MYSQL
    engine_version: Text = "5.7.mysql_aurora.2.07.2"
    port: PositiveInt = PositiveInt(3306)
    instance_size: Text = "db.t3.medium"
    snapshot_identifier: Optional[Text]
    family: Text = "aurora-mysql5.7"


class DTRDSInstance(ComponentResource):
    """
    Build an RDS Instance

    """

    def __init__(self, db_config: DTRDSConfig):
        """Create an RDS instance, parameter group, and optionally read replica.

        :param db_config: Configuration object for customizing the deployed database instance.
        :type db_config: DTRDSConfig

        :returns: The constructed component resource object.

        :rtype: DTRDSInstance
        """
        super().__init__(
            "diceytech:infrastructure:aws:database:DTRDSInstance",
            db_config.instance_name,
            None,
        )

        self.parameter_group = rds.ParameterGroup(
            f"{db_config.instance_name}-{db_config.engine}-parameter-group",
            # family=parameter_group_family(db_config.engine, db_config.engine_version),
            family=db_config.family,
            name=f"{db_config.instance_name}-{db_config.engine}-parameter-group",
        )

        self.db_instance = rds.Instance(
            f"{db_config.instance_name}-{db_config.engine}-instance",
            allocated_storage=db_config.storage,
            auto_minor_version_upgrade=True,
            backup_retention_period=db_config.backup_days,
            copy_tags_to_snapshot=True,
            db_subnet_group_name=db_config.subnet_group_name,
            deletion_protection=db_config.prevent_delete,
            engine=db_config.engine,
            engine_version=db_config.engine_version,
            final_snapshot_identifier=f"{db_config.instance_name}-{db_config.engine}-final-snapshot",
            identifier=db_config.instance_name,
            instance_class=db_config.instance_size,
            max_allocated_storage=db_config.max_storage,
            multi_az=db_config.multi_az,
            name=db_config.db_name,
            parameter_group_name=self.parameter_group.name,
            password=db_config.password.get_secret_value(),
            port=db_config.port,
            publicly_accessible=db_config.is_public,
            skip_final_snapshot=not db_config.take_final_snapshot,
            storage_encrypted=True,
            storage_type=db_config.storage_type.value,
            tags=db_config.tags,
            username=db_config.username,
            vpc_security_group_ids=[group.id for group in db_config.security_groups],
            snapshot_identifier=db_config.snapshot_identifier,
        )

        component_outputs = {
            "parameter_group": self.parameter_group,
            "rds_instance": self.db_instance,
        }

        self.register_outputs(component_outputs)

    def get_endpoint(self) -> str:
        return self.db_instance.endpoint


class DTAuroraCluster(ComponentResource):
    """
    Build an Aurora Cluster

    """

    def __init__(self, db_config: DTRDSConfig):
        """Create an DTMySQLConfig, parameter group, and optionally read replica.

        :param db_config: Configuration object for customizing the deployed database instance.
        :type db_config: DTAuroraConfig

        :returns: The constructed component resource object.

        :rtype: DTAuroraCluster
        """
        super().__init__(
            "diceytech:infrastructure:aws:database:DTAuroraCluster",
            db_config.instance_name,
            None,
        )
        """
        self.parameter_group = rds.ParameterGroup(
            f"{db_config.instance_name}-{db_config.engine}-parameter-group",
            # family=parameter_group_family(db_config.engine, db_config.engine_version),
            family=db_config.family,
            name=f"{db_config.instance_name}-{db_config.engine}-parameter-group",
        )
        """
        self.db_cluster = rds.Cluster(
            f"{db_config.instance_name}-{db_config.engine}-instance",
            backup_retention_period=db_config.backup_days,
            copy_tags_to_snapshot=True,
            db_subnet_group_name=db_config.subnet_group_name,
            deletion_protection=db_config.prevent_delete,
            cluster_identifier=db_config.instance_name,
            engine=db_config.engine,
            engine_version=db_config.engine_version,
            final_snapshot_identifier=f"{db_config.instance_name}-{db_config.engine}-final-snapshot",
            # db_cluster_parameter_group_name=self.parameter_group.name,
            master_password=db_config.password.get_secret_value(),
            port=db_config.port,
            skip_final_snapshot=not db_config.take_final_snapshot,
            tags=db_config.tags,
            master_username=db_config.username,
            vpc_security_group_ids=[group.id for group in db_config.security_groups],
            # snapshot_identifier=db_config.snapshot_identifier,
        )

        self.cluster_instances = []
        self.cluster_instances.append(
            rds.ClusterInstance(
                f"{db_config.instance_name}-{db_config.engine}-instance-0",
                identifier=db_config.instance_name,
                cluster_identifier=self.db_cluster.id,
                engine=db_config.engine,
                engine_version=db_config.engine_version,
                instance_class=db_config.instance_size,
                tags=db_config.tags,
            )
        )

        component_outputs = {
            # "parameter_group": self.parameter_group,
            "aurora_cluster": self.db_cluster,
            "aurora_instances": self.cluster_instances,
        }

        self.register_outputs(component_outputs)

    def get_endpoint(self) -> str:
        return self.db_cluster.endpoint
