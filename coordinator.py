import logging
import xml.etree.ElementTree as ET
from datetime import timedelta
from urllib.parse import quote

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class CiructorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, device_id: str) -> None:
        self.host = host
        self.device_id = device_id
        self._url = f"http://{host}/services/user/values.xml?id={quote(device_id, safe='')}"
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_id}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(self._url) as response:
                        response.raise_for_status()
                        text = await response.text()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error comunicando con {self.host}: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error inesperado: {err}") from err

        return self._parse_xml(text)

    def _parse_xml(self, xml_text: str) -> dict:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as err:
            raise UpdateFailed(f"Error parseando XML: {err}") from err

        data: dict = {}
        prefix = f"{self.device_id}."

        for variable in root.findall("variable"):
            id_elem = variable.find("id")
            if id_elem is None or not id_elem.text:
                continue

            var_id = id_elem.text.strip()
            if not var_id.startswith(prefix):
                continue

            key = var_id[len(prefix):]

            value_elem = variable.find("value")
            text_value_elem = variable.find("textValue")

            if value_elem is not None and value_elem.text and value_elem.text.strip():
                try:
                    data[key] = float(value_elem.text.strip())
                except ValueError:
                    data[key] = value_elem.text.strip()
            elif text_value_elem is not None and text_value_elem.text:
                data[key] = text_value_elem.text.strip()

        return data
