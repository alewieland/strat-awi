import asyncio
from typing import Dict

from ib_async import IB, util
from ib_async.contract import Stock
from ib_async.order import LimitOrder

from thetagang.ibkr import IBKR


async def buy_etfs(account: str, weights: Dict[str, float]) -> None:
    ib = IB()
    ibkr = IBKR(ib, api_response_wait_time=60, default_order_exchange="SMART")
    ib.connect("127.0.0.1", 7497, clientId=1, account=account)

    summary = await ibkr.account_summary(account)
    nlv = float(next(v.value for v in summary if v.tag == "NetLiquidation"))

    for symbol, weight in weights.items():
        ticker = await ibkr.get_ticker_for_stock(symbol, "SMART")
        price = ticker.marketPrice()
        if not price or price <= 0:
            continue
        qty = int((nlv * weight) // price)
        if qty <= 0:
            continue
        contract = Stock(symbol, "SMART", "USD")
        order = LimitOrder("BUY", qty, price)
        ibkr.place_order(contract, order)
        print(f"Submitted order: BUY {qty} {symbol} @ {price}")

    ib.disconnect()


def main() -> None:
    weights = {"VT": 0.75, "SPY": 0.5, "QQQ": 0.5}
    asyncio.run(buy_etfs("DU1234567", weights))


if __name__ == "__main__":
    util.patchAsyncio()
    main()
