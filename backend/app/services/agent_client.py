from typing import Any, Dict, Optional
import httpx
from app.config import settings
from app.core.logging import logger
from app.core.exceptions import GovernanceException


class AgentHTTPClient:
    """
    Asynchronous HTTP client for real inter-agent network communication.
    """
    _test_client: Optional[httpx.AsyncClient] = None

    @classmethod
    def set_test_client(cls, client: Optional[httpx.AsyncClient]) -> None:
        """Inject test ASGI client for automated in-process HTTP tests."""
        cls._test_client = client

    @classmethod
    def get_base_url(cls) -> str:
        """Get base URL for agent HTTP network calls."""
        return f"http://127.0.0.1:{settings.PORT}"

    @classmethod
    async def post_to_agent(
        cls,
        endpoint_path: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send a real asynchronous HTTP POST request to downstream agent endpoint.
        """
        effective_timeout = timeout or settings.HTTP_TIMEOUT_SECONDS

        # 1. Use injected test client if present (e.g. during in-process tests)
        if cls._test_client is not None:
            try:
                response = await cls._test_client.post(
                    endpoint_path,
                    json=payload,
                    headers=headers,
                    timeout=effective_timeout
                )
                if response.status_code >= 400:
                    try:
                        err_json = response.json()
                        msg = err_json.get("message", response.text)
                        err_code = err_json.get("error_code", f"HTTP_{response.status_code}")
                    except Exception:
                        msg = response.text
                        err_code = f"HTTP_{response.status_code}"
                    raise GovernanceException(
                        message=f"Downstream agent returned error ({response.status_code}): {msg}",
                        error_code=err_code,
                        status_code=response.status_code
                    )
                return response.json()
            except httpx.TimeoutException:
                logger.error(f"HTTP timeout calling {endpoint_path} after {effective_timeout}s")
                raise GovernanceException(
                    message=f"Timeout communicating with downstream agent at {endpoint_path}",
                    error_code="AGENT_COMMUNICATION_TIMEOUT",
                    status_code=504
                )

        # 2. Real HTTP over network
        full_url = f"{cls.get_base_url()}{endpoint_path}"
        async with httpx.AsyncClient(timeout=effective_timeout) as client:
            try:
                response = await client.post(full_url, json=payload, headers=headers)
                if response.status_code >= 400:
                    try:
                        err_json = response.json()
                        msg = err_json.get("message", response.text)
                        err_code = err_json.get("error_code", f"HTTP_{response.status_code}")
                    except Exception:
                        msg = response.text
                        err_code = f"HTTP_{response.status_code}"
                    raise GovernanceException(
                        message=f"Downstream agent returned error ({response.status_code}): {msg}",
                        error_code=err_code,
                        status_code=response.status_code
                    )
                return response.json()
            except httpx.TimeoutException:
                logger.error(f"HTTP timeout calling {full_url} after {effective_timeout}s")
                raise GovernanceException(
                    message=f"Timeout communicating with downstream agent at {endpoint_path}",
                    error_code="AGENT_COMMUNICATION_TIMEOUT",
                    status_code=504
                )
            except httpx.RequestError as e:
                logger.error(f"Network error calling {full_url}: {e}")
                raise GovernanceException(
                    message=f"Failed to communicate with downstream agent: {str(e)}",
                    error_code="AGENT_NETWORK_ERROR",
                    status_code=502
                )
