import pulumi
import pytest

from educate_infrastructure.databases.database import DTRDSInstance, DTMySQLConfig


class TestDTVpc(object):
    """ Initial tests doing basic coverage """

    def setup(self):
        self.config = DTMySQLConfig()

        self.rds = DTRDSInstance(db_config=self.config)

    @pulumi.runtime.test
    def test_rds_created(self):
        def check_name(args):
            pass

        return pulumi.Output.all(self.rds).apply(check_name)
