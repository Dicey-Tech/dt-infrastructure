import pulumi


# https://github.com/pulumi/pulumi/blob/8a9b381767c5d14ad2181c41ede4266cd196c839/sdk/python/lib/pulumi/runtime/mocks.py#L40
class PulumiMock(pulumi.runtime.Mocks):
    """Pulumi component for mocking pulumi engine."""

    def call(self, token, args, provider):
        # https://github.com/pulumi/pulumi-aws/blob/ddc4d5623c8bb2e25428f11ab0de487b17795614/sdk/python/pulumi_aws/get_availability_zones.py#L206
        if token == "aws:index/getAvailabilityZones:getAvailabilityZones":
            return {"names": ["eu-west-2a", "eu-west-2b", "eu-west-2c"]}

        return {}

    def new_resource(self, token, name, inputs, provider, id_):
        outputs = inputs
        if token == "aws:ec2/vpc:Vpc":
            outputs = inputs
        return [name + "_id", outputs]


pulumi.runtime.set_mocks(PulumiMock())