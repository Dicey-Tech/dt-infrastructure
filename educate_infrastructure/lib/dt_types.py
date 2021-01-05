from enum import Enum
from typing import Dict, Text

from pydantic import BaseModel

# https://github.com/mitodl/ol-infrastructure/blob/9cd2cfe20e6f731d2d46caf7fe4458daf53d6163/src/ol_infrastructure/lib/ol_types.py#L45
class AWSBase(BaseModel):
    """Base class for deriving configuration objects to pass to AWS component resources."""

    tags: Dict
    region: Text = "eu-west-2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tags.update({"pulumi_managed": "true"})