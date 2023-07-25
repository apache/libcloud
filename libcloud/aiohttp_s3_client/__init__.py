from .client import S3Client
from .version import __version__, version_info
from .xml import AwsObjectMeta


__all__ = (
    "__version__",
    "version_info",
    "AwsObjectMeta",
    "S3Client",
)
