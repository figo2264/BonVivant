# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hanlyang Stock is a Korean stock automated trading system using the Korea Investment Securities API. It implements a **hybrid strategy** combining technical analysis and news sentiment analysis (using Claude API) to make buy/sell decisions.

**Primary Language**: Korean (코드 주석, 설정, 문서 모두 한국어)

## Common Commands

```bash
# Run the live trading strategy (cron target)
python strategy.py                          # Default: simulation mode, small_capital preset
TRADE_MODE=real python strategy.py          # Real trading mode
STRATEGY_PRESET=balanced python strategy.py # Different preset

# Run backtests
python run_modular_backtest.py              # Basic backtest with settings UI
python run_news_backtest.py                 # Backtest with news sentiment analysis
python run_technical_optimization.py        # Technical analysis parameter optimization

# Install dependencies (uses uv package manager)
uv sync

# Python version
python --version  # Requires Python 3.11+
```

## Architecture

### Core Package Structure (`hanlyang_stock/`)

```
hanlyang_stock/
├── config/
│   ├── settings.py           # HantuStock API & Slack config (singleton)
│   ├── strategy_settings.py  # Strategy presets: conservative/balanced/aggressive/small_capital
│   └── backtest_settings.py  # Backtest-specific configurations
├── strategy/
│   ├── executor.py           # SellExecutor, BuyExecutor - main trading logic
│   ├── selector.py           # Stock selection based on technical analysis
│   └── news_based_selector.py # Hybrid selection with news sentiment
├── analysis/
│   ├── technical.py          # Technical indicators (RSI, MA, Bollinger, PSAR)
│   ├── news_sentiment.py     # News crawler + Claude API sentiment analysis
│   └── crawlers/             # Naver Finance news crawlers (Selenium-based)
├── backtest/
│   ├── engine.py             # Main backtest engine
│   ├── portfolio.py          # Portfolio simulation
│   └── performance.py        # Performance metrics calculation
├── data/
│   ├── fetcher.py            # Stock data from HantuStock/pykrx/FinanceDataReader
│   └── preprocessor.py       # Data normalization
└── utils/
    ├── storage.py            # Runtime data management (strategy_data.json)
    ├── notification.py       # Slack notifications
    └── data_validator.py     # Stock data validation
```

### Key Entry Points

- **`strategy.py`**: Main cron target. Executes sell at 08:30, buy at 15:20 KST
- **`HantuStock.py`**: Korea Investment Securities API wrapper (bid/ask/holdings)
- **`run_modular_backtest.py`**: Interactive backtest runner with multiple presets

### Strategy Configuration

Settings are managed in `hanlyang_stock/config/strategy_settings.py` with dataclasses:

```python
# Presets: 'conservative', 'balanced', 'aggressive', 'small_capital'
from hanlyang_stock.config.strategy_settings import get_strategy_config
config = get_strategy_config('balanced')
```

Key parameters per preset:
- `max_selections`: Max stocks to select per day
- `stop_loss_rate`: Loss limit (e.g., -0.03 for -3%)
- `technical_weight` / `news_weight`: Hybrid strategy weights
- `min_technical_score`: Minimum score threshold for selection
- `investment_amounts`: Investment per confidence level

### Trading Modes

Set via environment variable `TRADE_MODE`:
- `simulation` (default): Uses mock trading API endpoint
- `real`: Uses live trading API endpoint

### Data Flow

1. **Stock Selection** (`selector.py`): Filters KOSPI/KOSDAQ stocks by market cap, trading volume, technical indicators
2. **Technical Analysis** (`technical.py`): Calculates scores using RSI, moving averages, Bollinger Bands, Parabolic SAR
3. **News Sentiment** (`news_sentiment.py`): Crawls Naver Finance news, analyzes with Claude API for 1/5/10/20 day predictions
4. **Execution** (`executor.py`): Combines scores, applies pyramiding logic, executes via HantuStock API

### Configuration Files

- `config.yaml`: API keys and account info (real/simulation)
- `strategy_data.json`: Runtime data (holding periods, purchase info, performance logs)
- `.env`: `ANTHROPIC_API_KEY` for Claude API

## Important Patterns

### Stop-Loss Priority
매도 로직에서 손실 제한이 최우선:
1. Stop-loss (-3% ~ -8% based on preset)
2. News-based sell signal (if hybrid strategy)
3. Maximum holding period (5 days basic, 10 days hybrid)

### Pyramiding
`pyramiding_enabled` allows additional buys into existing positions:
- Requires 75%+ technical score
- Resets holding period on high-score additional buy
- Max 2 resets per position

### Trend Strength Filter
Weighted scoring system for entry signals:
- Parabolic SAR (35%), RSI rebound (25%), Support level (20%), Volume surge (10%), Candle size (10%)
- Minimum score threshold varies by preset (0.50 - 0.70)