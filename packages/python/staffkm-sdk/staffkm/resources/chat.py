"""Chat resource — supports streaming."""
from __future__ import annotations

import json
from typing import Iterator
import httpx


class ChatResource:
    def __init__(self, http: httpx.Client):
        self._http = http

    def send(
        self,
        application_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> dict:
        """Non-streaming chat."""
        body: dict = {"user_input": message}
        if conversation_id:
            body["conversation_id"] = conversation_id
        r = self._http.post(f"/api/v1/applications/{application_id}/chat", json=body)
        r.raise_for_status()
        return r.json()

    def stream(
        self,
        application_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> Iterator[str]:
        """SSE streaming chat — yields token strings."""
        body: dict = {"user_input": message}
        if conversation_id:
            body["conversation_id"] = conversation_id
        with self._http.stream(
            "POST",
            f"/api/v1/applications/{application_id}/chat",
            json=body,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and "token" in parsed:
                        yield parsed["token"]
                    else:
                        yield str(parsed)
                except json.JSONDecodeError:
                    yield data
