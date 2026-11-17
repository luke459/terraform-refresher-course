"""Primary regions supported by course connections and lab inputs."""
from typing import Literal, get_args

AWSRegion = Literal['eu-west-1', 'us-east-1', 'eu-west-2']
SUPPORTED_REGIONS = get_args(AWSRegion)
