import os
import requests

class VpsClient:
    def __init__(self):
        self.base_url = os.getenv("VPS_BASE_URL")
        self.headers = {
            "Authorization": f"Bearer {os.getenv('BRIDGE_TOKEN')}",
            "Content-Type": "application/json"
        }

    def post(self, path, payload):
        r = requests.post(f"{self.base_url}{path}", json=payload, headers=self.headers, timeout=15)
        r.raise_for_status()
        return r.json()

    def heartbeat(self):
        return self.post("/bridge/ibkr/heartbeat", {})

    def send_executions(self, executions):
        if executions:
            return self.post("/bridge/ibkr/executions", {"executions": executions})

    def send_positions(self, positions):
        if positions:
            return self.post("/bridge/ibkr/positions", {"positions": positions})

    def send_open_orders(self, orders):
        if orders:
            return self.post("/bridge/ibkr/open-orders", {"orders": orders})