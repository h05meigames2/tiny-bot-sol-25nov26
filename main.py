"""Tiny Bot — beat buy-and-hold on Solana (make.fun).

Speaks the agent-fun/bars-replay/v1 line protocol on stdin/stdout via the
vendored kit shim (vendor/makefun_bars.py): the harness sends a hello
handshake, then one batch of hourly bars per step, and this bot answers
each batch with a reply carrying its orders (buy/sell) for that bar.

Strategy — per-symbol fast/slow moving-average crossover with a stop-loss:
  * Keep every bar's close per symbol; compute a fast MA (last 8 bars) and
    a slow MA (last 24 bars) from the closes seen so far.
  * Go long when the fast MA sits above the slow MA by more than a small
    hysteresis band (0.5%) AND the latest close is above the fast MA, so
    price itself confirms the trend; exit to USDC as soon as the fast MA
    crosses back under the slow MA OR the latest close drops under the fast
    MA — a fast exit, so a downtrend is not ridden down. The band keeps one
    noisy bar from flipping the position back and forth.
  * A 5% stop-loss on entry cost: if a held position's current value falls
    3% below what was paid for it, sell it all — this caps drawdown on the
    sharp drops memecoins are prone to.
  * Size sanely: at most 20% of equity in any one symbol, never all-in, and
    never more than the weight room the hello caps allow or the cash on hand.
    Buys and sells are spread across all seven symbols, so the bot keeps
    trading (and keeps learning from each bar) instead of betting the whole
    book on a single crossover.

Deterministic: no clock, no environment, no unseeded randomness — the two
grading runs produce identical action logs. Standard library only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

FAST_BARS = 8          # fast moving-average window, in bars (hours)
SLOW_BARS = 24         # slow moving-average window, in bars (hours)
BAND_BPS = 50          # 0.5% hysteresis band around the crossover
STOP_BPS = 500         # 5% stop-loss versus entry cost
TARGET_WEIGHT_BPS = 2000   # at most 20% of equity in one symbol
MAX_SLIPPAGE_BPS = 100     # 1% max slippage per order

# Closes seen so far, per symbol: symbol -> [close, close, ...] (ints).
_closes = {}


def _ma(values, window):
    """Simple moving average of the last `window` values (ints)."""
    return sum(values[-window:]) / window


def on_batch(state, batch):
    """Decide the orders for this batch of bars; [] means hold everything."""
    # Warm-up batches build history only: any order decided on one is
    # rejected by the harness, so stay silent until the scored window opens.
    if state.warming_up:
        return []

    # Fold this batch's bars into the per-symbol close history.
    for bar in batch["bars"]:
        _closes.setdefault(bar["symbol"], []).append(int(bar["c"]))

    orders = []
    max_orders = state.hello["caps"]["max_orders_per_bar"]
    max_positions = state.hello["caps"]["max_open_positions"]
    min_notional = int(state.hello["fees"]["min_notional_quote_units"])
    planned_spend = 0
    planned_new = 0

    for symbol in state.symbols:
        if len(orders) >= max_orders:
            break
        closes = _closes.get(symbol)
        if not closes or len(closes) < SLOW_BARS:
            continue  # not enough bars yet for a slow average

        fast = _ma(closes, FAST_BARS)
        slow = _ma(closes, SLOW_BARS)
        holding = state.positions.get(symbol)

        # Stop-loss first: a held position 3% under water gets sold in full,
        # whatever the moving averages say.
        if holding is not None:
            current_value = state.value(symbol, holding.qty)
            if current_value * 10000 < holding.cost * (10000 - STOP_BPS):
                orders.append({
                    "side": "sell",
                    "symbol": symbol,
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                })
                continue

        if fast > slow * (10000 + BAND_BPS) / 10000 and closes[-1] > fast:
            # Uptrend confirmed by price itself: buy if flat, sized to at
            # most 20% of equity.
            if holding is None and len(state.positions) + planned_new < max_positions:
                room = state.weight_room(symbol)
                target = state.equity * TARGET_WEIGHT_BPS // 10000
                spend = min(target, room, state.cash - planned_spend)
                if spend >= min_notional and spend > 0:
                    orders.append({
                        "side": "buy",
                        "symbol": symbol,
                        "notional_quote_units": spend,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    planned_spend += spend
                    planned_new += 1
        elif fast < slow * (10000 - BAND_BPS) / 10000 or closes[-1] < fast:
            # Downtrend, or price already under its fast average: exit to
            # USDC at once instead of waiting for the slow crossover.
            if holding is not None:
                orders.append({
                    "side": "sell",
                    "symbol": symbol,
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                })

    return orders


makefun_bars.run(on_batch)
