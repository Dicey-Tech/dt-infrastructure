import pytest
import pulumi

# from educate_infrastructure.applications.educate.tests
import educate_mock

# from educate_infrastructure.applications.educate.ec2
from ..ec2 import DTEc2


class TestEducateApp(object):
    """ Initial tests doing some basic coverage"""

    def setup(self):
        self.name = "educate-app-instance"
        self.instance = DTEc2(name=self.name)

    @pulumi.runtime.test
    def test_ec2_has_required_tags(self):
        def check_tags(args):
            urn, tags = args
            assert tags is not None
            assert "pulumi_managed" in tags

        return pulumi.Output.all(self.instance.urn, self.instance.tags).apply(
            check_tags
        )
