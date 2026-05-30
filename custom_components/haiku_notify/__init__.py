"""Haiku Notify integration.

Wraps an existing notify service with an LLM rephrasing layer so chained
reminders don't read like the same script being recited over and over.

For each configured entry we register a legacy notify service
``notify.<name>`` that accepts the same payload as the wrapped service.
Each call:

1. Loads recent history bucketed by ``data.source_id``.
2. Asks ``ai_task.generate_data`` to rephrase the current message in light
   of that history, preserving every concrete data point verbatim.
3. Forwards the rephrased text to the wrapped notify service.
4. Updates and persists history.

Any failure in the rephrase step falls back to forwarding the original
message untouched, so notifications are never dropped.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_HISTORY_SIZE,
    CONF_INSTRUCTIONS,
    CONF_NAME,
    CONF_PERSONAS,
    CONF_PERSONAS_ENABLED,
    CONF_WRAPPED_SERVICE,
    DATA_SOURCE_ID,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_INSTRUCTIONS,
    DEFAULT_PERSONAS,
    DEFAULT_PERSONAS_ENABLED,
    DOMAIN,
    STORAGE_KEY_TEMPLATE,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

NOTIFY_DOMAIN = "notify"
AI_TASK_DOMAIN = "ai_task"
AI_TASK_SERVICE = "generate_data"
AI_TASK_TIMEOUT_SECONDS = 15
TASK_NAME = "haiku_notify_rephrase"
DEFAULT_SOURCE_ID = "_default"

NOTIFY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("target"): vol.Any(cv.string, [cv.string]),
        vol.Optional("data"): dict,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Haiku Notify from a config entry."""
    config = {**entry.data, **entry.options}
    name: str = config[CONF_NAME]
    wrapped_service: str = config[CONF_WRAPPED_SERVICE]
    ai_task_entity: str = config[CONF_AI_TASK_ENTITY]
    history_size: int = config.get(CONF_HISTORY_SIZE, DEFAULT_HISTORY_SIZE)
    instructions: str = (
        config.get(CONF_INSTRUCTIONS) or DEFAULT_INSTRUCTIONS
    ).strip() or DEFAULT_INSTRUCTIONS
    personas_enabled: bool = config.get(CONF_PERSONAS_ENABLED, DEFAULT_PERSONAS_ENABLED)
    personas_raw: str = config.get(CONF_PERSONAS, DEFAULT_PERSONAS)
    personas: list[str] = [
        p.strip() for p in personas_raw.splitlines() if p.strip()
    ]

    store: Store[dict[str, list[str]]] = Store(
        hass,
        STORAGE_VERSION,
        STORAGE_KEY_TEMPLATE.format(entry_id=entry.entry_id),
    )
    history: dict[str, list[str]] = await store.async_load() or {}

    handler = _NotifyHandler(
        hass=hass,
        wrapped_service=wrapped_service,
        ai_task_entity=ai_task_entity,
        history_size=history_size,
        instructions=instructions,
        personas_enabled=personas_enabled,
        personas=personas,
        store=store,
        history=history,
    )

    hass.services.async_register(
        NOTIFY_DOMAIN,
        name,
        handler.handle_call,
        schema=NOTIFY_SERVICE_SCHEMA,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "history": history,
        "service_name": name,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data is not None:
        hass.services.async_remove(NOTIFY_DOMAIN, entry_data["service_name"])
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change so the new wrapped service / model takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)


class _NotifyHandler:
    """Per-config-entry handler that rephrases then forwards notify calls."""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        wrapped_service: str,
        ai_task_entity: str,
        history_size: int,
        instructions: str,
        personas_enabled: bool,
        personas: list[str],
        store: Store[dict[str, list[str]]],
        history: dict[str, list[str]],
    ) -> None:
        self.hass = hass
        self.wrapped_service = wrapped_service
        self.ai_task_entity = ai_task_entity
        self.history_size = history_size
        self.instructions = instructions
        self.personas_enabled = personas_enabled
        self.personas = personas
        self.store = store
        self.history = history
        self._lock = asyncio.Lock()

    async def handle_call(self, call: ServiceCall) -> None:
        message: str = call.data["message"]
        title: str | None = call.data.get("title")
        target = call.data.get("target")
        passthrough_data: dict[str, Any] = dict(call.data.get("data") or {})

        source_id = str(passthrough_data.pop(DATA_SOURCE_ID, DEFAULT_SOURCE_ID))
        recent = list(self.history.get(source_id, []))

        should_rephrase = bool(recent) or (self.personas_enabled and self.personas)
        rephrased = await self._rephrase(message, recent) if should_rephrase else message

        forward_data: dict[str, Any] = {"message": rephrased}
        if title is not None:
            forward_data["title"] = title
        if target is not None:
            forward_data["target"] = target
        if passthrough_data:
            forward_data["data"] = passthrough_data

        domain, service = self.wrapped_service.split(".", 1)
        try:
            await self.hass.services.async_call(
                domain, service, forward_data, blocking=True
            )
        except HomeAssistantError:
            _LOGGER.exception(
                "Failed to forward notification to %s", self.wrapped_service
            )
            raise

        await self._record(source_id, message)

    async def _rephrase(self, current: str, recent: list[str]) -> str:
        """Call ai_task to rephrase. On any failure, return the original."""
        instructions = self.instructions
        if self.personas_enabled and self.personas:
            persona = random.choice(self.personas)
            instructions = f"PERSONA: {persona}.\n\n{instructions}"

        history_block = "\n".join(f"- {line}" for line in recent)
        prompt = (
            f"{instructions}\n\n"
            f"Recent prior notifications from this source (oldest first):\n"
            f"{history_block}\n\n"
            f"CURRENT MESSAGE TO REPHRASE:\n{current}"
        )

        try:
            result = await asyncio.wait_for(
                self.hass.services.async_call(
                    AI_TASK_DOMAIN,
                    AI_TASK_SERVICE,
                    {
                        "task_name": TASK_NAME,
                        "instructions": prompt,
                        ATTR_ENTITY_ID: self.ai_task_entity,
                    },
                    blocking=True,
                    return_response=True,
                ),
                timeout=AI_TASK_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, HomeAssistantError):
            _LOGGER.warning(
                "ai_task.generate_data failed; forwarding original message"
            )
            return current

        rephrased = _extract_text(result)
        if not rephrased or not rephrased.strip():
            _LOGGER.warning("ai_task returned empty text; forwarding original")
            return current
        return rephrased.strip()

    async def _record(self, source_id: str, message: str) -> None:
        async with self._lock:
            bucket = self.history.setdefault(source_id, [])
            bucket.append(message)
            if len(bucket) > self.history_size:
                del bucket[: len(bucket) - self.history_size]
            await self.store.async_save(self.history)


def _extract_text(result: Any) -> str | None:
    """ai_task.generate_data returns {'data': <text or dict>, ...}."""
    if not isinstance(result, dict):
        return None
    data = result.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("text", "message", "output"):
            value = data.get(key)
            if isinstance(value, str):
                return value
    return None
