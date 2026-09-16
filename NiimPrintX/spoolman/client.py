"""Minimal client for the Spoolman REST API (https://donkie.github.io/Spoolman/)."""
import requests

from .exception import SpoolmanError

DEFAULT_TIMEOUT = 10


class SpoolmanClient:
    def __init__(self, base_url, timeout=DEFAULT_TIMEOUT):
        if not base_url or not base_url.strip():
            raise SpoolmanError("Spoolman server URL is not set.")
        self.root_url = self._normalize_root_url(base_url)
        self.base_url = f"{self.root_url}/api/v1"
        self.timeout = timeout
        self.session = requests.Session()

    @staticmethod
    def _normalize_root_url(base_url):
        url = base_url.strip().rstrip("/")
        if url.endswith("/api/v1"):
            url = url[: -len("/api/v1")]
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        return url

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            raise SpoolmanError(f"Could not connect to Spoolman server at {self.root_url}.") from e
        except requests.exceptions.Timeout as e:
            raise SpoolmanError("Connection to Spoolman server timed out.") from e
        except requests.exceptions.HTTPError as e:
            raise SpoolmanError(f"Spoolman server returned an error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise SpoolmanError(f"Failed to reach Spoolman server: {e}") from e
        return response.json()

    def get_spools(self, *, name=None, material=None, vendor=None, location=None, archived=False):
        """List spools, optionally filtered. Mirrors GET /api/v1/spool."""
        params = {"allow_archived": "true" if archived else "false"}
        if name:
            params["filament.name"] = name
        if material:
            params["filament.material"] = material
        if vendor:
            params["filament.vendor.name"] = vendor
        if location:
            params["location"] = location
        return self._get("/spool", params=params)

    def get_spool(self, spool_id):
        return self._get(f"/spool/{spool_id}")

    def test_connection(self):
        self._get("/spool", params={"limit": 1})
        return True
