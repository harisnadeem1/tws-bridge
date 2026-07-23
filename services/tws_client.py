from ib_insync import IB, ExecutionFilter
from services.mapper import map_execution, map_position, map_open_trade
from services.state_store import StateStore


class TwsClient:
    def __init__(self, vps_client):
        self.ib = IB()
        self.vps = vps_client
        self.state = StateStore()

    def connect(self, host, port, client_id):
        print(f"[TWS] Trying connect to {host}:{port} clientId={client_id}", flush=True)

        self.ib.connect(host, port, clientId=client_id)
        print("[TWS] Connected successfully", flush=True)

        self.ib.execDetailsEvent += self.on_exec_details
        self.ib.openOrderEvent += self.on_open_order
        self.ib.orderStatusEvent += self.on_order_status

        self.sync_all()

    def sync_all(self):
        print("[TWS] Requesting current state...", flush=True)

        try:
            self.ib.reqOpenOrders()
        except Exception as e:
            print(f"[TWS] reqOpenOrders error: {e}", flush=True)

        try:
            self.ib.reqPositions()
        except Exception as e:
            print(f"[TWS] reqPositions error: {e}", flush=True)

        self.ib.sleep(2)

        try:
            print("[TWS] Requesting executions...", flush=True)
            fills = self.ib.reqExecutions(ExecutionFilter())
        except Exception as e:
            print(f"[TWS] reqExecutions error: {e}", flush=True)
            fills = []

        executions = []
        for fill in fills:
            exec_id = fill.execution.execId
            if self.state.should_send_exec(exec_id):
                executions.append(map_execution(fill))

        print(f"[TWS] Found {len(executions)} execution(s)", flush=True)
        if executions:
            print(f"[TWS] Sending executions: {executions}", flush=True)
        self.vps.send_executions(executions)

        positions = [map_position(p) for p in self.ib.positions()]
        print(f"[TWS] Found {len(positions)} position(s)", flush=True)
        if positions:
            print(f"[TWS] Sending positions: {positions}", flush=True)
        self.vps.send_positions(positions)

        orders = [map_open_trade(t) for t in self.ib.openTrades()]
        print(f"[TWS] Found {len(orders)} open order(s)", flush=True)
        if orders:
            print(f"[TWS] Sending open orders: {orders}", flush=True)
        self.vps.send_open_orders(orders)

    def on_exec_details(self, trade, fill):
        try:
            exec_id = fill.execution.execId
            if not self.state.should_send_exec(exec_id):
                return

            payload = map_execution(fill)
            print(f"[TWS] New execution event: {payload}", flush=True)
            self.vps.send_executions([payload])
        except Exception as e:
            print(f"[TWS] execDetailsEvent error: {e}", flush=True)

    def on_open_order(self, trade):
        try:
            payload = map_open_trade(trade)
            print(f"[TWS] Open order event: {payload}", flush=True)
            self.vps.send_open_orders([payload])
        except Exception as e:
            print(f"[TWS] openOrderEvent error: {e}", flush=True)

    def on_order_status(self, trade):
        try:
            payload = map_open_trade(trade)
            print(f"[TWS] Order status event: {payload}", flush=True)
            self.vps.send_open_orders([payload])
        except Exception as e:
            print(f"[TWS] orderStatusEvent error: {e}", flush=True)

    def run(self):
        print("[TWS] Entering IB event loop", flush=True)
        self.ib.run()