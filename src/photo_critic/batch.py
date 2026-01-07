"""Anthropic batch API client for submitting and polling batch requests."""

import logging
import os
import time
from typing import Any

from anthropic import Anthropic

logger = logging.getLogger(__name__)


class BatchClient:
    """Client for interacting with Anthropic's Message Batches API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize batch client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        if api_key is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=api_key)
        logger.info("Batch client initialized")

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        """Submit batch of requests to Anthropic API.

        Args:
            requests: List of batch request dictionaries

        Returns:
            Batch ID for polling

        Raises:
            ValueError: If requests list is empty or exceeds limits
            Exception: If API call fails
        """
        if not requests:
            raise ValueError("Cannot submit empty batch")

        if len(requests) > 10000:
            raise ValueError(
                f"Batch too large: {len(requests)} requests " "(max 10,000 per batch)"
            )

        logger.info(f"Submitting batch with {len(requests)} requests")

        try:
            # Create message batch
            batch = self.client.messages.batches.create(requests=requests)

            logger.info(f"Batch submitted successfully: {batch.id}")
            logger.info(f"Processing status: {batch.processing_status}")

            return batch.id

        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
            raise

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """Get status of a batch.

        Args:
            batch_id: Batch ID returned from submit_batch()

        Returns:
            Dictionary with batch status information

        Raises:
            Exception: If API call fails
        """
        try:
            batch = self.client.messages.batches.retrieve(batch_id)

            return {
                "id": batch.id,
                "processing_status": batch.processing_status,
                "request_counts": {
                    "processing": batch.request_counts.processing,
                    "succeeded": batch.request_counts.succeeded,
                    "errored": batch.request_counts.errored,
                    "canceled": batch.request_counts.canceled,
                    "expired": batch.request_counts.expired,
                },
                "ended_at": batch.ended_at,
                "created_at": batch.created_at,
                "expires_at": batch.expires_at,
            }

        except Exception as e:
            logger.error(f"Failed to get batch status: {e}")
            raise

    def poll_batch(
        self,
        batch_id: str,
        poll_interval: int = 30,
        timeout: int = 86400,  # 24 hours
    ) -> dict[str, Any]:
        """Poll batch until completion.

        Args:
            batch_id: Batch ID to poll
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final batch status dictionary

        Raises:
            TimeoutError: If batch doesn't complete within timeout
            Exception: If batch fails or API call fails
        """
        logger.info(f"Polling batch {batch_id} (interval={poll_interval}s)")

        start_time = time.time()
        last_log_time = start_time

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Batch {batch_id} did not complete within {timeout}s"
                )

            # Get status
            status = self.get_batch_status(batch_id)
            processing_status = status["processing_status"]

            # Log progress periodically (every 5 minutes)
            if time.time() - last_log_time >= 300:
                counts = status["request_counts"]
                logger.info(
                    f"Batch progress: "
                    f"{counts['succeeded']} succeeded, "
                    f"{counts['processing']} processing, "
                    f"{counts['errored']} errored"
                )
                last_log_time = time.time()

            # Check if ended
            if processing_status == "ended":
                counts = status["request_counts"]
                logger.info(
                    f"Batch completed: "
                    f"{counts['succeeded']} succeeded, "
                    f"{counts['errored']} errored, "
                    f"{counts['expired']} expired, "
                    f"{counts['canceled']} canceled"
                )
                return status

            # Check for other terminal states
            if processing_status in {"canceling", "canceled"}:
                raise Exception(f"Batch was canceled: {batch_id}")

            # Wait before next poll
            logger.debug(f"Batch still processing, waiting {poll_interval}s...")
            time.sleep(poll_interval)

    def get_batch_results(self, batch_id: str) -> list[dict[str, Any]]:
        """Retrieve results from completed batch.

        Args:
            batch_id: Batch ID of completed batch

        Returns:
            List of result dictionaries

        Raises:
            ValueError: If batch is not completed
            Exception: If API call fails
        """
        logger.info(f"Retrieving results for batch {batch_id}")

        try:
            # Get batch status first
            status = self.get_batch_status(batch_id)

            if status["processing_status"] != "ended":
                raise ValueError(f"Batch not completed: {status['processing_status']}")

            # Retrieve results
            results = []
            for result in self.client.messages.batches.results(batch_id):
                results.append(
                    {
                        "custom_id": result.custom_id,
                        "result": result.result,
                    }
                )

            logger.info(f"Retrieved {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve batch results: {e}")
            raise


def submit_batch(requests: list[dict[str, Any]], api_key: str | None = None) -> str:
    """Submit batch of requests to Anthropic API.

    Convenience function that creates a client and submits batch.

    Args:
        requests: List of batch request dictionaries
        api_key: Optional API key (defaults to ANTHROPIC_API_KEY env var)

    Returns:
        Batch ID for polling
    """
    client = BatchClient(api_key=api_key)
    return client.submit_batch(requests)


def poll_batch(
    batch_id: str,
    api_key: str | None = None,
    poll_interval: int = 30,
    timeout: int = 86400,
) -> dict[str, Any]:
    """Poll batch until completion.

    Convenience function that creates a client and polls batch.

    Args:
        batch_id: Batch ID to poll
        api_key: Optional API key (defaults to ANTHROPIC_API_KEY env var)
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait

    Returns:
        Final batch status dictionary
    """
    client = BatchClient(api_key=api_key)
    return client.poll_batch(batch_id, poll_interval, timeout)


def get_batch_results(
    batch_id: str, api_key: str | None = None
) -> list[dict[str, Any]]:
    """Retrieve results from completed batch.

    Convenience function that creates a client and retrieves results.

    Args:
        batch_id: Batch ID of completed batch
        api_key: Optional API key (defaults to ANTHROPIC_API_KEY env var)

    Returns:
        List of result dictionaries
    """
    client = BatchClient(api_key=api_key)
    return client.get_batch_results(batch_id)
