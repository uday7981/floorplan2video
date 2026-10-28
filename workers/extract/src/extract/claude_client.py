"""Claude vision call. Forces a single `save_plan` tool call whose input
matches the Plan JSON Schema. One repair round on validation failure.

Reads model name from env (ANTHROPIC_MODEL) and never hard-codes it (hard rule).

Prompt text comes from prompts/templates.yaml so prompt tweaks don't need a code
change. Fallback: embedded copy that matches the YAML, used when the templates
file isn't on disk (e.g. in unit tests that stub out the client).
"""
from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from plan_schema import Plan

log = logging.getLogger(__name__)


# ------------------------- prompt loading -------------------------

_FALLBACK_SYSTEM = (
    "You convert architectural floor plans into structured geometry.\n"
    "Return the plan only by calling the save_plan tool. Never reply in prose.\n\n"
    "Rules:\n"
    "- Units are metres. Origin is the bottom-left of the building, x right, y up.\n"
    "- Read dimension text first. If none is readable, use a scale bar. If neither\n"
    "  exists, use known_dimension_m from the user if provided. Record which in\n"
    "  meta.scale_source.\n"
    "- Model every wall as a centreline segment with thickness. Join walls at\n"
    "  corners so endpoints match exactly.\n"
    "- Doors, windows and open passages are openings on a wall, measured from the\n"
    "  wall's start point to the opening centre.\n"
    "- Every labelled space becomes a room with a closed polygon inside the walls.\n"
    "- Mark exactly one exterior door as main_entrance.\n"
    "- If anything is guessed, lower meta.confidence and add a warning."
)


def load_system_prompt() -> str:
    """Load prompts/templates.yaml extraction.system; fallback to the embedded copy."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "prompts" / "templates.yaml"
        if candidate.exists():
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(candidate.read_text())
                return data["extraction"]["system"].strip()
            except Exception as e:
                log.warning("templates.yaml load failed (%s); using embedded fallback", e)
                break
    return _FALLBACK_SYSTEM


# ------------------------- types -------------------------

@dataclass
class ExtractResult:
    plan_json: dict[str, Any]
    input_tokens: int
    output_tokens: int
    repaired: bool  # True if we needed a second attempt


class AnthropicLike(Protocol):
    """Minimal subset of anthropic.Anthropic we rely on. Tests pass a fake."""
    def __call__(self, **kwargs) -> Any: ...


# ------------------------- client -------------------------

class ClaudeExtractor:
    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        max_tokens: int = 4096,
        _client: Any = None,
    ) -> None:
        self.model = model or os.environ.get("ANTHROPIC_MODEL")
        if not self.model:
            raise RuntimeError("ANTHROPIC_MODEL not set")
        if _client is not None:
            self.client = _client
        else:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.max_tokens = max_tokens
        self.system_prompt = load_system_prompt()
        self.tool_schema = Plan.model_json_schema()

    # ---- public ----

    def extract(self, png_bytes: bytes, *, known_dim_m: float | None = None) -> ExtractResult:
        """Call Claude once; if the result fails Pydantic validation, send the
        errors back for one repair round. Returns ExtractResult with totals."""
        image_block = self._image_block(png_bytes)
        user_text = self._user_text(known_dim_m)

        messages = [
            {"role": "user", "content": [image_block, {"type": "text", "text": user_text}]}
        ]
        resp = self._call(messages)
        tool_use, plan_dict = self._extract_tool_input(resp)
        in_tokens = resp.usage.input_tokens
        out_tokens = resp.usage.output_tokens

        try:
            Plan.model_validate(plan_dict)
            return ExtractResult(plan_dict, in_tokens, out_tokens, repaired=False)
        except Exception as e:
            log.info("first-pass validation failed; attempting repair")
            errors = str(e)

        # Repair round.
        messages += [
            {"role": "assistant", "content": resp.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use["id"],
                        "content": (
                            f"The plan failed validation with these errors:\n{errors}\n\n"
                            f"Call save_plan again with a corrected plan."
                        ),
                        "is_error": True,
                    }
                ],
            },
        ]
        resp2 = self._call(messages)
        _, plan_dict2 = self._extract_tool_input(resp2)
        in_tokens += resp2.usage.input_tokens
        out_tokens += resp2.usage.output_tokens

        Plan.model_validate(plan_dict2)  # raises if still invalid; caller handles
        return ExtractResult(plan_dict2, in_tokens, out_tokens, repaired=True)

    # ---- helpers ----

    def _call(self, messages: list[dict]) -> Any:
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            tools=[{
                "name": "save_plan",
                "description": "Save the extracted floor plan as plan JSON.",
                "input_schema": self.tool_schema,
            }],
            tool_choice={"type": "tool", "name": "save_plan"},
            messages=messages,
        )

    @staticmethod
    def _image_block(png_bytes: bytes) -> dict:
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.b64encode(png_bytes).decode("ascii"),
            },
        }

    @staticmethod
    def _user_text(known_dim_m: float | None) -> str:
        base = "Here is the floor plan. Call save_plan with the extracted geometry."
        if known_dim_m:
            base += f"\n\nKnown dimension: overall width is {known_dim_m:.3f} m."
        return base

    @staticmethod
    def _extract_tool_input(resp: Any) -> tuple[dict, dict]:
        """Pull the tool_use block out of a Claude response. Returns (tool_use_dict, input_dict)."""
        for block in resp.content:
            btype = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
            if btype == "tool_use":
                tu = block if isinstance(block, dict) else {
                    "id": block.id, "name": block.name, "input": block.input,
                }
                return tu, tu["input"]
        raise RuntimeError("Claude response contained no tool_use block")
