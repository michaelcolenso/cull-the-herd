"""Batch API clients for submitting and polling batch requests."""

import json
import logging
import os
import tempfile
import time
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _read_binary_response(content: Any) -> str:
    if hasattr(content, "read"):
        data = content.read()
    elif isinstance(content, (bytes, bytearray)):
        data = content
    else:
        data = getattr(content, "content", content)
    if isinstance(data, str):
        return data
    return data.decode("utf-8")


def _extract_openai_text(body: dict[str, Any]) -> str | None:
    choices = body.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                return part.get("text")
    return None


class AnthropicBatchClient:
    """Client for interacting with Anthropic's Message Batches API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize batch client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        raise NotImplementedError(
            "Anthropic provider is disabled for now. Use OpenAI instead."
        )

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


class OpenAIBatchClient:
    """Client for interacting with OpenAI's Batch API."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str = "/v1/chat/completions",
        completion_window: str = "24h",
    ) -> None:
        """Initialize batch client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            endpoint: Batch endpoint to target
            completion_window: OpenAI completion window

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        load_dotenv()
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(api_key=api_key)
        self.endpoint = endpoint
        self.completion_window = completion_window
        logger.info("OpenAI batch client initialized")

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        """Submit batch of requests to OpenAI API.

        Args:
            requests: List of batch request dictionaries

        Returns:
            Batch ID for polling
        """
        if not requests:
            raise ValueError("Cannot submit empty batch")

        logger.info(f"Submitting OpenAI batch with {len(requests)} requests")
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".jsonl", delete=False, encoding="utf-8"
            ) as handle:
                for request in requests:
                    handle.write(json.dumps(request))
                    handle.write("\n")
                temp_path = handle.name

            with open(temp_path, "rb") as handle:
                input_file = self.client.files.create(
                    file=handle, purpose="batch"
                )

            batch = self.client.batches.create(
                input_file_id=input_file.id,
                endpoint=self.endpoint,
                completion_window=self.completion_window,
            )

            logger.info(f"Batch submitted successfully: {batch.id}")
            logger.info(f"Processing status: {batch.status}")

            return batch.id

        except Exception as e:
            logger.error(f"Failed to submit OpenAI batch: {e}")
            raise

        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError as e:
                    logger.warning(f"Failed to remove temp file {temp_path}: {e}")

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        """Get status of a batch.

        Args:
            batch_id: Batch ID returned from submit_batch()

        Returns:
            Dictionary with batch status information
        """
        try:
            batch = self.client.batches.retrieve(batch_id)
            counts = _get_value(batch, "request_counts", {})
            total = _get_value(counts, "total", 0) or 0
            completed = _get_value(counts, "completed", 0) or 0
            failed = _get_value(counts, "failed", 0) or 0
            processing = max(total - completed - failed, 0)
            status = _get_value(batch, "status", "in_progress")

            return {
                "id": batch.id,
                "processing_status": "ended"
                if status == "completed"
                else "in_progress",
                "provider_status": status,
                "request_counts": {
                    "processing": processing,
                    "succeeded": completed,
                    "errored": failed,
                    "canceled": 0,
                    "expired": 0,
                },
                "ended_at": _get_value(batch, "completed_at"),
                "created_at": _get_value(batch, "created_at"),
                "expires_at": _get_value(batch, "expires_at"),
                "output_file_id": _get_value(batch, "output_file_id"),
                "error_file_id": _get_value(batch, "error_file_id"),
            }

        except Exception as e:
            logger.error(f"Failed to get OpenAI batch status: {e}")
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
        logger.info(f"Polling OpenAI batch {batch_id} (interval={poll_interval}s)")

        start_time = time.time()
        last_log_time = start_time

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Batch {batch_id} did not complete within {timeout}s"
                )

            status = self.get_batch_status(batch_id)
            provider_status = status.get("provider_status")

            if time.time() - last_log_time >= 300:
                counts = status["request_counts"]
                logger.info(
                    f"Batch progress: "
                    f"{counts['succeeded']} succeeded, "
                    f"{counts['processing']} processing, "
                    f"{counts['errored']} errored"
                )
                last_log_time = time.time()

            if provider_status == "completed":
                logger.info(
                    f"Batch completed: "
                    f"{status['request_counts']['succeeded']} succeeded, "
                    f"{status['request_counts']['errored']} errored"
                )
                return status

            if provider_status in {"failed", "expired", "canceled"}:
                raise Exception(f"Batch failed with status: {provider_status}")

            logger.debug(
                f"Batch still processing ({provider_status}), "
                f"waiting {poll_interval}s..."
            )
            time.sleep(poll_interval)

    def get_batch_results(self, batch_id: str) -> list[dict[str, Any]]:
        """Retrieve results from completed batch.

        Args:
            batch_id: Batch ID of completed batch

        Returns:
            List of result dictionaries
        """
        logger.info(f"Retrieving OpenAI results for batch {batch_id}")

        try:
            status = self.get_batch_status(batch_id)
            if status.get("provider_status") != "completed":
                raise ValueError(
                    f"Batch not completed: {status.get('provider_status')}"
                )

            output_file_id = status.get("output_file_id")
            if not output_file_id:
                raise ValueError("No output_file_id available for batch")

            content = self.client.files.content(output_file_id)
            raw_text = _read_binary_response(content)

            results = []
            for line in raw_text.splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                custom_id = record.get("custom_id", "unknown")
                response = record.get("response") or {}
                status_code = response.get("status_code")
                if status_code == 200:
                    body = response.get("body", {})
                    text_content = _extract_openai_text(body)
                    result_obj = {
                        "type": "succeeded" if text_content else "errored",
                        "message": {
                            "content": [
                                {"type": "text", "text": text_content or ""}
                            ]
                        },
                    }
                else:
                    error_detail = record.get("error") or response.get("body")
                    result_obj = {
                        "type": "errored",
                        "error": error_detail,
                    }

                results.append({"custom_id": custom_id, "result": result_obj})

            logger.info(f"Retrieved {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve OpenAI batch results: {e}")
            raise


class BatchClient:
    """Client for interacting with supported batch APIs."""

    def __init__(
        self, provider: str = "openai", api_key: str | None = None
    ) -> None:
        provider_normalized = provider.lower()
        if provider_normalized == "anthropic":
            raise NotImplementedError(
                "Anthropic provider is disabled for now. Use --provider openai."
            )
        elif provider_normalized == "openai":
            self.client = OpenAIBatchClient(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        self.provider = provider_normalized

    def submit_batch(self, requests: list[dict[str, Any]]) -> str:
        return self.client.submit_batch(requests)

    def get_batch_status(self, batch_id: str) -> dict[str, Any]:
        return self.client.get_batch_status(batch_id)

    def poll_batch(
        self,
        batch_id: str,
        poll_interval: int = 30,
        timeout: int = 86400,
    ) -> dict[str, Any]:
        return self.client.poll_batch(
            batch_id, poll_interval=poll_interval, timeout=timeout
        )

    def get_batch_results(self, batch_id: str) -> list[dict[str, Any]]:
        return self.client.get_batch_results(batch_id)


def submit_batch(
    requests: list[dict[str, Any]],
    api_key: str | None = None,
    provider: str = "openai",
) -> str:
    """Submit batch of requests to a supported API.

    Convenience function that creates a client and submits batch.

    Args:
        requests: List of batch request dictionaries
        api_key: Optional API key (provider-specific env var is fallback)
        provider: "openai"

    Returns:
        Batch ID for polling
    """
    client = BatchClient(provider=provider, api_key=api_key)
    return client.submit_batch(requests)


def poll_batch(
    batch_id: str,
    api_key: str | None = None,
    poll_interval: int = 30,
    timeout: int = 86400,
    provider: str = "openai",
) -> dict[str, Any]:
    """Poll batch until completion.

    Convenience function that creates a client and polls batch.

    Args:
        batch_id: Batch ID to poll
        api_key: Optional API key (provider-specific env var is fallback)
        poll_interval: Seconds between status checks
        timeout: Maximum seconds to wait
        provider: "openai"

    Returns:
        Final batch status dictionary
    """
    client = BatchClient(provider=provider, api_key=api_key)
    return client.poll_batch(batch_id, poll_interval, timeout)


def get_batch_results(
    batch_id: str,
    api_key: str | None = None,
    provider: str = "openai",
) -> list[dict[str, Any]]:
    """Retrieve results from completed batch.

    Convenience function that creates a client and retrieves results.

    Args:
        batch_id: Batch ID of completed batch
        api_key: Optional API key (provider-specific env var is fallback)
        provider: "openai"

    Returns:
        List of result dictionaries
    """
    client = BatchClient(provider=provider, api_key=api_key)
    return client.get_batch_results(batch_id)
