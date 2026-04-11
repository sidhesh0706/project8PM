import json
from dataclasses import dataclass
from typing import Any
from urllib import parse, request


@dataclass
class HelpdeskEnvClient:
    base_url: str

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base_url.rstrip('/')}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        with request.urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, params: dict[str, Any] | None = None, payload: dict | None = None) -> dict:
        url = f"{self.base_url.rstrip('/')}{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = request.Request(url, data=data, headers=headers, method="POST")
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def health(self) -> dict:
        return self._get("/health")

    def tasks(self) -> dict:
        return self._get("/tasks")

    def reset(self, task_name: str) -> dict:
        return self._post("/reset", payload={"task_name": task_name})

    def step(self, session_id: str, operation: dict) -> dict:
        return self._post("/step", payload={"session_id": session_id, "operations": [operation]})

    def state(self, session_id: str) -> dict:
        return self._get("/state", params={"session_id": session_id})
