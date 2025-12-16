from typing import Any, Dict
from datetime import datetime

import httpx

from app.api.core.config import settings
from app.api.core.logging import get_logger

logger = get_logger(__name__)


class ExternalAPIError(Exception):
    """Raised when external API call fails."""

    pass


class ExternalAPIService:
    """
    Service for calling external APIs and normalizing responses.

    Handles HTTP requests to external services with retries, timeouts,
    and response normalization.
    """

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize the external API service.

        Args:
            base_url: Base URL for the external API (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = base_url or settings.external_api_url
        self.timeout = timeout or settings.external_api_timeout
        self.max_retries = settings.external_api_max_retries

        logger.info(
            "external_api_service_initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    async def call_api(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict[str, Any] | None = None,
        headers: Dict[str, str] | None = None,
        credentials: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Call external API endpoint.

        Args:
            endpoint: API endpoint (e.g., "/posts" or "/users/1")
            method: HTTP method (GET, POST, PUT, DELETE)
            params: Query parameters
            headers: HTTP headers
            credentials: Client credentials to include in request

        Returns:
            Dict[str, Any]: Normalized API response

        Raises:
            ExternalAPIError: If API call fails after retries
        """
        # Build full URL
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Prepare headers
        request_headers = headers or {}
        if credentials:
            # Add credentials to headers (common pattern)
            if "api_key" in credentials:
                request_headers["Authorization"] = f"Bearer {credentials['api_key']}"
            if "api_token" in credentials:
                request_headers["X-API-Token"] = credentials["api_token"]

        logger.info(
            "calling_external_api",
            url=url,
            method=method,
            has_params=params is not None,
            has_credentials=credentials is not None,
        )

        # Make the API call with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        params=params,
                        headers=request_headers,
                    )

                    # Check for HTTP errors
                    response.raise_for_status()

                    # Parse JSON response
                    data = response.json()

                    logger.info(
                        "external_api_call_success",
                        url=url,
                        method=method,
                        status_code=response.status_code,
                        response_size=len(response.content),
                    )

                    # Normalize and return the response
                    return self.normalize_response(data, url, method)

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "external_api_http_error",
                    url=url,
                    method=method,
                    status_code=e.response.status_code,
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                if attempt >= self.max_retries:
                    raise ExternalAPIError(
                        f"API call failed with status {e.response.status_code}: {e.response.text}"
                    )

            except httpx.TimeoutException:
                logger.warning(
                    "external_api_timeout",
                    url=url,
                    method=method,
                    timeout=self.timeout,
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                if attempt >= self.max_retries:
                    raise ExternalAPIError(f"API call timed out after {self.timeout}s")

            except httpx.RequestError as e:
                logger.error(
                    "external_api_request_error",
                    url=url,
                    method=method,
                    error=str(e),
                    attempt=attempt,
                    max_retries=self.max_retries,
                )

                if attempt >= self.max_retries:
                    raise ExternalAPIError(f"API request failed: {e}")

            except Exception as e:
                logger.error(
                    "external_api_unexpected_error",
                    url=url,
                    method=method,
                    error=str(e),
                    exc_info=True,
                )
                raise ExternalAPIError(f"Unexpected error during API call: {e}")

        raise ExternalAPIError("API call failed after max retries")

    def normalize_response(
        self, data: Any, url: str, method: str
    ) -> Dict[str, Any]:
        """
        Normalize external API response to a consistent format.

        Args:
            data: Raw API response data
            url: URL that was called
            method: HTTP method used

        Returns:
            Dict[str, Any]: Normalized response with metadata

        Example normalized response:
            {
                "data": [...],  # Original response data
                "metadata": {
                    "source_url": "https://api.example.com/posts",
                    "method": "GET",
                    "fetched_at": "2024-01-01T00:00:00",
                    "record_count": 10,
                    "data_type": "list"
                }
            }
        """
        # Determine data type
        if isinstance(data, list):
            data_type = "list"
            record_count = len(data)
        elif isinstance(data, dict):
            data_type = "object"
            record_count = len(data.keys())
        else:
            data_type = type(data).__name__
            record_count = 1

        # Create normalized response
        normalized = {
            "data": data,
            "metadata": {
                "source_url": url,
                "method": method,
                "fetched_at": datetime.utcnow().isoformat(),
                "record_count": record_count,
                "data_type": data_type,
            },
        }

        logger.debug(
            "response_normalized",
            data_type=data_type,
            record_count=record_count,
        )

        return normalized


def get_external_api_service(
    base_url: str | None = None, timeout: int | None = None
) -> ExternalAPIService:
    """
    Get an external API service instance.

    Args:
        base_url: Optional custom base URL
        timeout: Optional custom timeout

    Returns:
        ExternalAPIService: Service instance
    """
    return ExternalAPIService(base_url=base_url, timeout=timeout)
