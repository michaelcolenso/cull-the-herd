"""Photo Critic - AI-powered batch photo criticism using vision APIs."""

__version__ = "0.1.0"
__author__ = "Michael Colenso"
__email__ = "github@michaelcolenso.com"

from photo_critic.batch import (
    BatchClient,
    OpenAIBatchClient,
    poll_batch,
    submit_batch,
)
from photo_critic.discovery import discover_images
from photo_critic.prepare import prepare_batch, preprocess_image
from photo_critic.report import generate_report

__all__ = [
    "discover_images",
    "preprocess_image",
    "prepare_batch",
    "submit_batch",
    "poll_batch",
    "generate_report",
    "BatchClient",
    "OpenAIBatchClient",
]
