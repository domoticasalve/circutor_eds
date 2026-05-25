import logging
from urllib.parse import quote

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_CVM,
    DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID, default="CVM-A"): str,
        vol.Required(CONF_DEVICE_NAME, default="CVM-A"): str,
        vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_CVM): SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"value": k, "label": v} for k, v in DEVICE_TYPES.items()
                ],
                mode=SelectSelectorMode.LIST,
            )
        ),
    }
)


async def _validate_connection(host: str, device_id: str) -> None:
    url = f"http://{host}/services/user/values.xml?id={quote(device_id, safe='')}"
    async with async_timeout.timeout(10):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                if "<values>" not in content:
                    raise ValueError("Respuesta XML no valida")


class CiructorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            device_id = user_input[CONF_DEVICE_ID].strip()
            device_name = user_input[CONF_DEVICE_NAME].strip()
            device_type = user_input[CONF_DEVICE_TYPE]

            unique_id = f"{host}_{device_id}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await _validate_connection(host, device_id)
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except ValueError:
                errors["base"] = "invalid_response"
            except Exception:
                _LOGGER.exception("Error inesperado durante la configuracion")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"{device_name} ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_DEVICE_ID: device_id,
                        CONF_DEVICE_NAME: device_name,
                        CONF_DEVICE_TYPE: device_type,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
