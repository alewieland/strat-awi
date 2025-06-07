import math
from datetime import date, timedelta

from ib_async import Option, Order, PortfolioItem
from ib_async.contract import Stock

from thetagang.config import (
    AccountConfig,
    Config,
    OptionChainsConfig,
    RollWhenConfig,
    SymbolConfig,
    TargetConfig,
)
from thetagang.util import (
    calculate_net_short_positions,
    position_pnl,
    weighted_avg_long_strike,
    weighted_avg_short_strike,
    would_increase_spread,
)


def _base_config(symbol: SymbolConfig, target: TargetConfig | None = None) -> Config:
    return Config(
        account=AccountConfig(number="TEST", margin_usage=1.0),
        option_chains=OptionChainsConfig(expirations=1, strikes=1),
        roll_when=RollWhenConfig(dte=1),
        target=target or TargetConfig(dte=1, minimum_open_interest=0),
        symbols={"SPY": symbol},
    )


def test_position_pnl() -> None:
    qqq_put = PortfolioItem(
        contract=Option(
            conId=397556522,
            symbol="QQQ",
            lastTradeDateOrContractMonth="20201218",
            strike=300.0,
            right="P",
            multiplier="100",
            primaryExchange="AMEX",
            currency="USD",
            localSymbol="QQQ   201218P00300000",
            tradingClass="QQQ",
        ),
        position=-1.0,
        marketPrice=4.1194396,
        marketValue=-411.94,
        averageCost=222.4293,
        unrealizedPNL=-189.51,
        realizedPNL=0.0,
        account="DU2962946",
    )
    assert round(position_pnl(qqq_put), 2) == -0.85

    spy = PortfolioItem(
        contract=Stock(
            conId=756733,
            symbol="SPY",
            right="0",
            primaryExchange="ARCA",
            currency="USD",
            localSymbol="SPY",
            tradingClass="SPY",
        ),
        position=100.0,
        marketPrice=365.4960022,
        marketValue=36549.6,
        averageCost=368.42,
        unrealizedPNL=-292.4,
        realizedPNL=0.0,
        account="DU2962946",
    )
    assert round(position_pnl(spy), 4) == -0.0079

    spy_call = PortfolioItem(
        contract=Option(
            conId=454208258,
            symbol="SPY",
            lastTradeDateOrContractMonth="20201214",
            strike=373.0,
            right="C",
            multiplier="100",
            primaryExchange="AMEX",
            currency="USD",
            localSymbol="SPY   201214C00373000",
            tradingClass="SPY",
        ),
        position=-1.0,
        marketPrice=2.7256999,
        marketValue=-272.57,
        averageCost=565.76,
        unrealizedPNL=293.19,
        realizedPNL=0.0,
        account="DU2962946",
    )
    assert round(position_pnl(spy_call), 2) == 0.52

    spy_put = PortfolioItem(
        contract=Option(
            conId=458705534,
            symbol="SPY",
            lastTradeDateOrContractMonth="20210122",
            strike=352.5,
            right="P",
            multiplier="100",
            primaryExchange="AMEX",
            currency="USD",
            localSymbol="SPY   210122P00352500",
            tradingClass="SPY",
        ),
        position=-1.0,
        marketPrice=5.96710015,
        marketValue=-596.71,
        averageCost=528.9025,
        unrealizedPNL=-67.81,
        realizedPNL=0.0,
        account="DU2962946",
    )
    assert round(position_pnl(spy_put), 2) == -0.13


def test_get_delta() -> None:
    target_config = TargetConfig(dte=1, minimum_open_interest=0, delta=0.5)
    symbol_config = SymbolConfig(weight=1.0)
    config = _base_config(symbol_config, target_config)
    assert 0.5 == config.get_target_delta("SPY", "P")
    assert 0.5 == config.get_target_delta("SPY", "C")

    target_config = TargetConfig(
        dte=1,
        minimum_open_interest=0,
        delta=0.5,
        puts=TargetConfig.Puts(delta=0.4),
    )
    config = _base_config(symbol_config, target_config)
    assert 0.4 == config.get_target_delta("SPY", "P")

    target_config = TargetConfig(
        dte=1,
        minimum_open_interest=0,
        delta=0.5,
        calls=TargetConfig.Calls(delta=0.4),
    )
    config = _base_config(symbol_config, target_config)
    assert 0.5 == config.get_target_delta("SPY", "P")

    config = _base_config(symbol_config, target_config)
    assert 0.4 == config.get_target_delta("SPY", "C")

    symbol_config = SymbolConfig(weight=1.0, delta=0.3)
    config = _base_config(symbol_config, target_config)
    assert 0.3 == config.get_target_delta("SPY", "C")

    symbol_config = SymbolConfig(
        weight=1.0,
        delta=0.3,
        puts=SymbolConfig.Puts(delta=0.2),
    )
    config = _base_config(symbol_config, target_config)
    assert 0.3 == config.get_target_delta("SPY", "C")
    assert 0.2 == config.get_target_delta("SPY", "P")


def con(dte: str, strike: float, right: str, position: float) -> PortfolioItem:
    return PortfolioItem(
        contract=Option(
            conId=458705534,
            symbol="SPY",
            lastTradeDateOrContractMonth=dte,
            strike=strike,
            right=right,
            multiplier="100",
            primaryExchange="AMEX",
            currency="USD",
            localSymbol="SPY   210122P00352500",
            tradingClass="SPY",
        ),
        position=position,
        marketPrice=5.96710015,
        marketValue=-596.71,
        averageCost=528.9025,
        unrealizedPNL=-67.81,
        realizedPNL=0.0,
        account="DU2962946",
    )


def test_calculate_net_short_positions() -> None:
    today = date.today()
    exp3dte = (today + timedelta(days=3)).strftime("%Y%m%d")
    exp30dte = (today + timedelta(days=30)).strftime("%Y%m%d")
    exp90dte = (today + timedelta(days=90)).strftime("%Y%m%d")

    assert 1 == calculate_net_short_positions([con(exp3dte, 69, "P", -1)], "P")

    assert 1 == calculate_net_short_positions(
        [con(exp3dte, 69, "P", -1), con(exp3dte, 69, "C", 1)], "P"
    )

    assert 0 == calculate_net_short_positions(
        [con(exp3dte, 69, "P", -1), con(exp3dte, 69, "C", 1)], "C"
    )

    assert 0 == calculate_net_short_positions(
        [con(exp3dte, 69, "C", -1), con(exp3dte, 69, "C", 1)], "C"
    )

    assert 0 == calculate_net_short_positions(
        [
            con(exp3dte, 69, "C", -1),
            con(exp3dte, 69, "C", 1),
            con(exp30dte, 69, "C", 1),
        ],
        "C",
    )

    assert 0 == calculate_net_short_positions(
        [
            con(exp3dte, 69, "C", -1),
            con(exp3dte, 69, "P", -1),
            con(exp3dte, 69, "C", 1),
            con(exp30dte, 69, "C", 1),
        ],
        "C",
    )

    assert 0 == calculate_net_short_positions(
        [
            con(exp3dte, 69, "C", -1),
            con(exp3dte, 69, "P", -1),
            con(exp3dte, 69, "C", 1),
            con(exp30dte, 70, "C", 1),
        ],
        "C",
    )

    assert 1 == calculate_net_short_positions(
        [
            con(exp3dte, 69, "C", -1),
            con(exp3dte, 69, "C", -1),
            con(exp3dte, 69, "C", 1),
            con(exp30dte, 70, "C", 1),
        ],
        "C",
    )


def test_weighted_avg_strike() -> None:
    # both short
    assert math.isclose(weighted_avg_short_strike([con("", 50, "C", -1), con("", 40, "P", -1)], "C"), 50)
    assert math.isclose(weighted_avg_short_strike([con("", 50, "C", -1), con("", 40, "P", -1)], "P"), 40)

    # mix of short/long
    assert math.isclose(weighted_avg_short_strike([con("", 50, "C", -1), con("", 40, "P", 1)], "C"), 50)
    assert math.isclose(weighted_avg_long_strike([con("", 50, "C", 1), con("", 40, "P", 1)], "P"), 40)


def test_would_increase_spread() -> None:
    # Test BUY order with lmtPrice < 0 and updated_price > lmtPrice
    order1 = Order(action="BUY", lmtPrice=-10)
    updated_price1 = -5.0
    assert would_increase_spread(order1, updated_price1) is False

    # Test BUY order with lmtPrice < 0 and updated_price < lmtPrice
    order2 = Order(action="BUY", lmtPrice=-10)
    updated_price2 = -15.0
    assert would_increase_spread(order2, updated_price2) is True

    # Test BUY order with lmtPrice > 0 and updated_price < lmtPrice
    order3 = Order(action="BUY", lmtPrice=10)
    updated_price3 = 5.0
    assert would_increase_spread(order3, updated_price3) is True

    # Test BUY order with lmtPrice > 0 and updated_price > lmtPrice
    order4 = Order(action="BUY", lmtPrice=10)
    updated_price4 = 15.0
    assert would_increase_spread(order4, updated_price4) is False

    # Test SELL order with lmtPrice < 0 and updated_price < lmtPrice
    order5 = Order(action="SELL", lmtPrice=-10)
    updated_price5 = -15.0
    assert would_increase_spread(order5, updated_price5) is False

    # Test SELL order with lmtPrice < 0 and updated_price > lmtPrice
    order6 = Order(action="SELL", lmtPrice=-10)
    updated_price6 = -5.0
    assert would_increase_spread(order6, updated_price6) is True

    # Test SELL order with lmtPrice > 0 and updated_price > lmtPrice
    order7 = Order(action="SELL", lmtPrice=10)
    updated_price7 = 15.0
    assert would_increase_spread(order7, updated_price7) is True

    # Test SELL order with lmtPrice > 0 and updated_price < lmtPrice
    order8 = Order(action="SELL", lmtPrice=10)
    updated_price8 = 5.0
    assert would_increase_spread(order8, updated_price8) is False
