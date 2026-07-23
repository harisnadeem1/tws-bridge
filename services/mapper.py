def map_execution(fill):
    contract = fill.contract
    execution = fill.execution
    commission = fill.commissionReport.commission if fill.commissionReport else 0

    return {
        "execId": execution.execId,
        "orderId": execution.orderId,
        "symbol": contract.symbol,
        "localSymbol": getattr(contract, "localSymbol", None),
        "secType": getattr(contract, "secType", None),
        "side": "BUY" if execution.side == "BOT" else "SELL",
        "shares": float(execution.shares),
        "price": float(execution.price),
        "time": execution.time.isoformat() if execution.time else None,
        "commission": float(commission or 0),
        "currency": contract.currency or "USD"
    }


def map_position(position):
    return {
        "account": position.account,
        "symbol": position.contract.symbol,
        "quantity": float(position.position),
        "avgCost": float(position.avgCost),
        "currency": position.contract.currency
    }


def map_open_trade(trade):
    order = trade.order
    contract = trade.contract
    order_status = trade.orderStatus

    return {
        "orderId": order.orderId,
        "parentId": getattr(order, "parentId", 0),
        "permId": getattr(order, "permId", 0),
        "symbol": contract.symbol,
        "localSymbol": getattr(contract, "localSymbol", None),
        "secType": getattr(contract, "secType", None),
        "action": order.action,
        "orderType": order.orderType,
        "totalQuantity": float(order.totalQuantity or 0),
        "lmtPrice": None if order.lmtPrice in (None, 1.7976931348623157e+308) else float(order.lmtPrice),
        "auxPrice": None if order.auxPrice in (None, 1.7976931348623157e+308) else float(order.auxPrice),
        "status": order_status.status
    }