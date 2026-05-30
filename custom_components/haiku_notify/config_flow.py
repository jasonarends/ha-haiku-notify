"""Config flow for Haiku Notify."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_HISTORY_SIZE,
    CONF_INSTRUCTIONS,
    CONF_NAME,
    CONF_PERSONAS,
    CONF_PERSONAS_ENABLED,
    CONF_WRAPPED_SERVICE,
    DEFAULT_HISTORY_SIZE,
    DEFAULT_INSTRUCTIONS,
    DEFAULT_PERSONAS,
    DEFAULT_PERSONAS_ENABLED,
    DOMAIN,
    MAX_HISTORY_SIZE,
)


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(
            CONF_NAME,
            default=defaults.get(CONF_NAME, "haiku_discord"),
        ): str,
        vol.Required(
            CONF_WRAPPED_SERVICE,
            default=defaults.get(
                CONF_WRAPPED_SERVICE, "notify.discord_automations"
            ),
        ): str,
    }
    if CONF_AI_TASK_ENTITY in defaults:
        schema[vol.Required(
            CONF_AI_TASK_ENTITY, default=defaults[CONF_AI_TASK_ENTITY]
        )] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="ai_task"),
        )
    else:
        schema[vol.Required(CONF_AI_TASK_ENTITY)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="ai_task"),
        )
    schema[vol.Optional(
        CONF_HISTORY_SIZE,
        default=defaults.get(CONF_HISTORY_SIZE, DEFAULT_HISTORY_SIZE),
    )] = vol.All(int, vol.Range(min=1, max=MAX_HISTORY_SIZE))
    schema[vol.Optional(
        CONF_INSTRUCTIONS,
        default=defaults.get(CONF_INSTRUCTIONS, DEFAULT_INSTRUCTIONS),
    )] = selector.TextSelector(
        selector.TextSelectorConfig(multiline=True),
    )
    schema[vol.Optional(
        CONF_PERSONAS_ENABLED,
        default=defaults.get(CONF_PERSONAS_ENABLED, DEFAULT_PERSONAS_ENABLED),
    )] = selector.BooleanSelector()
    schema[vol.Optional(
        CONF_PERSONAS,
        default=defaults.get(CONF_PERSONAS, DEFAULT_PERSONAS),
    )] = selector.TextSelector(
        selector.TextSelectorConfig(multiline=True),
    )
    return vol.Schema(schema)


def _validate_wrapped_service(value: str) -> str | None:
    """Return an error key if value isn't a plausible notify.* service id."""
    if not value.startswith("notify."):
        return "invalid_wrapped_service"
    remainder = value[len("notify.") :]
    if not remainder or "." in remainder:
        return "invalid_wrapped_service"
    if not all(ch.isalnum() or ch == "_" for ch in remainder):
        return "invalid_wrapped_service"
    return None


class HaikuNotifyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Haiku Notify."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            wrapped = user_input[CONF_WRAPPED_SERVICE]
            error = _validate_wrapped_service(wrapped)
            if error:
                errors[CONF_WRAPPED_SERVICE] = error
            else:
                await self.async_set_unique_id(
                    f"{wrapped}:{user_input[CONF_NAME]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(),
            errors=errors,
        )

    @classmethod
    @callback
    def async_get_options_flow(cls, config_entry: ConfigEntry) -> OptionsFlow:
        return HaikuNotifyOptionsFlow()


class HaikuNotifyOptionsFlow(OptionsFlow):
    """Allow editing wrapped service / model / history size / instructions after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_user_schema(defaults=current),
        )
