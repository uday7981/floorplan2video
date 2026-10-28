"""RunPod GraphQL client. We only need three operations:
  - pod_status(pod_id)       → 'RUNNING' | 'EXITED' | 'STOPPED' | ...
  - start_pod(pod_id)        → start a stopped pod
  - stop_pod(pod_id)         → stop a running pod

API ref: https://docs.runpod.io/api/
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


RUNPOD_GRAPHQL = "https://api.runpod.io/graphql"


@dataclass
class RunPodClient:
    api_key: str
    _client: httpx.Client | None = None

    def __post_init__(self):
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)

    def _post(self, query: str, variables: dict | None = None) -> dict:
        r = self._client.post(
            RUNPOD_GRAPHQL,
            params={"api_key": self.api_key},
            json={"query": query, "variables": variables or {}},
        )
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            raise RuntimeError(f"RunPod GraphQL error: {body['errors']}")
        return body["data"]

    def pod_status(self, pod_id: str) -> str:
        data = self._post(
            """
            query pod($id: String!) {
              pod(input: {podId: $id}) {
                desiredStatus
                lastStatusChange
              }
            }
            """,
            {"id": pod_id},
        )
        return data["pod"]["desiredStatus"]

    def start_pod(self, pod_id: str) -> None:
        self._post(
            """
            mutation start($id: String!) {
              podResume(input: {podId: $id, gpuCount: 1}) {
                id
                desiredStatus
              }
            }
            """,
            {"id": pod_id},
        )

    def stop_pod(self, pod_id: str) -> None:
        self._post(
            """
            mutation stop($id: String!) {
              podStop(input: {podId: $id}) {
                id
                desiredStatus
              }
            }
            """,
            {"id": pod_id},
        )

    def ensure_running(self, pod_id: str) -> None:
        """Idempotent: start the pod if it isn't already running."""
        try:
            status = self.pod_status(pod_id)
        except Exception:
            status = "UNKNOWN"
        if status != "RUNNING":
            self.start_pod(pod_id)


def runpod_from_config(cfg):
    return RunPodClient(api_key=cfg.runpod_api_key)
