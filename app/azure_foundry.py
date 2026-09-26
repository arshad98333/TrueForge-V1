"""OpenAI-compatible bridge with Azure primary and optional OpenAI fallback."""

import json

import httpx
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from starlette.responses import StreamingResponse

SCOPE = "https://ai.azure.com/.default"


class AzureFoundryBridge:
    """Refresh Azure tokens locally and fail over only on provider availability errors."""

    FALLBACK_STATUSES = {401, 403, 404, 408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        endpoint: str,
        model: str,
        *,
        openai_api_key: str = "",
        openai_model: str = "",
        primary_transport=None,
        fallback_transport=None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.credential = DefaultAzureCredential()
        self.token_provider = get_bearer_token_provider(self.credential, SCOPE)
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model or model
        self.primary_transport = primary_transport
        self.fallback_transport = fallback_transport
        # This is also the supported direct Python client requested for smoke checks.
        self.client = OpenAI(base_url=self.endpoint, api_key=self.token_provider)

    def access_token(self) -> str:
        return self.token_provider()

    def probe(self):
        return self.client.responses.create(model=self.model, input="Reply with OK only.")

    async def _send(self, endpoint, path, body, headers, transport=None):
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=20, read=300, write=30, pool=20),
            transport=transport,
        )
        request = client.build_request(
            "POST", endpoint + path, content=body, headers=headers
        )
        try:
            return client, await client.send(request, stream=True)
        except Exception:
            await client.aclose()
            raise

    async def _forward(self, path: str, body: bytes):
        if len(body) > 2_000_000:
            raise ValueError("Azure model request exceeds 2 MB")
        token = await __import__("anyio").to_thread.run_sync(self.access_token)
        provider = "azure"
        try:
            client, response = await self._send(
                self.endpoint,
                path,
                body,
                {
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
                },
                self.primary_transport,
            )
        except Exception:
            if not self.openai_api_key:
                raise
            client, response, provider = await self._openai(path, body)
        if response.status_code in self.FALLBACK_STATUSES and self.openai_api_key:
            await response.aclose()
            await client.aclose()
            client, response, provider = await self._openai(path, body)

        async def content():
            try:
                async for chunk in response.aiter_raw():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        headers = {}
        for name in ("content-type", "cache-control", "x-request-id", "apim-request-id"):
            if value := response.headers.get(name):
                headers[name] = value
        headers["x-resolver-model-provider"] = provider
        return StreamingResponse(content(), status_code=response.status_code, headers=headers)

    async def _openai(self, path: str, body: bytes):
        payload = json.loads(body)
        payload["model"] = self.openai_model
        client, response = await self._send(
            "https://api.openai.com/v1",
            path,
            json.dumps(payload).encode(),
            {
                "Authorization": "Bearer " + self.openai_api_key,
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
            },
            self.fallback_transport,
        )
        return client, response, "openai-fallback"

    async def responses(self, body: bytes):
        return await self._forward("/responses", body)

    async def chat_completions(self, body: bytes):
        return await self._forward("/chat/completions", body)
