"""
Defines constants and objects used in PortfolioStrategy App.
"""

from enum import Enum


APP_NAME = "PortfolioStrategy"


class EngineType(Enum):
    LIVE = "实盘"
    BACKTESTING = "回测"

class BacktestingMode(Enum):
    BAR = 1
    TICK = 2



EVENT_PORTFOLIO_LOG = "ePortfolioLog"
EVENT_PORTFOLIO_STRATEGY = "ePortfolioStrategy"
