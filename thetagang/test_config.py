from thetagang.config import (
    AccountConfig,
    Config,
    OptionChainsConfig,
    RollWhenConfig,
    SymbolConfig,
    TargetConfig,
)


def _base_config(symbol: SymbolConfig) -> Config:
    return Config(
        account=AccountConfig(number="TEST", margin_usage=1.0),
        option_chains=OptionChainsConfig(expirations=1, strikes=1),
        roll_when=RollWhenConfig(dte=1),
        target=TargetConfig(dte=1, minimum_open_interest=0),
        symbols={"AAPL": symbol},
    )


def test_trading_is_allowed_with_symbol_no_trading() -> None:
    config = _base_config(SymbolConfig(no_trading=True, weight=1.0))
    assert not config.trading_is_allowed("AAPL")


def test_trading_is_allowed_with_symbol_trading_allowed() -> None:
    config = _base_config(SymbolConfig(no_trading=False, weight=1.0))
    assert config.trading_is_allowed("AAPL")
