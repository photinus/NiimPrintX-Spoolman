import threading

from NiimPrintX.spoolman.client import SpoolmanClient
from NiimPrintX.spoolman.exception import SpoolmanError


class SpoolmanOperation:
    def __init__(self, root):
        self.root = root
        self.client = None

    def connect(self, base_url):
        """Create and store a client for base_url. Raises SpoolmanError on a bad URL."""
        self.client = SpoolmanClient(base_url)
        return self.client

    def fetch_spools(self, on_success, on_error, **filters):
        if not self.client:
            on_error("Connect to a Spoolman server first.")
            return

        def worker():
            try:
                spools = self.client.get_spools(**filters)
            except SpoolmanError as e:
                message = str(e)
                self.root.after(0, lambda: on_error(message))
                return
            self.root.after(0, lambda: on_success(spools))

        threading.Thread(target=worker, daemon=True).start()
