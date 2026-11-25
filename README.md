# Tiny Bot — Beat Buy-and-Hold on Solana

[![make.fun](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/competitions/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![Rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/h05meigames2/tiny-bot-sol-25nov26/rank.svg)](https://make.fun/competitions/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![Reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/h05meigames2/tiny-bot-sol-25nov26/reward.svg)](https://make.fun/competitions/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

Entry for the [Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana bounty](https://make.fun/competitions/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1) ($2, entries close 27 Nov 2026 07:00 WIB).

## Strategy

A per-symbol moving-average crossover bot with a stop-loss, run across all seven symbols (SOL, WETH, WIF, RAY, JITOSOL, POPCAT, FARTCOIN):

- **Trend:** long when the 8-hour moving average sits more than 0.5% above the 24-hour moving average and the latest close is above the fast average (price itself confirms the trend); exit to USDC as soon as the fast average crosses back under the slow one or the latest close drops under the fast average — a fast exit, so a downtrend is not ridden down. The hysteresis band stops a single noisy bar from flipping the position.
- **Stop-loss:** any held position that falls 5% below its entry cost is sold in full, capping drawdown on sharp memecoin drops.
- **Sizing:** at most 20% of equity in any one symbol, never all-in, and never beyond the weight room or cash on hand — so the bot keeps trading through the whole window instead of betting the book on one crossover.

## How it works

`main.py` (Python 3.13, standard library only) speaks the `agent-fun/bars-replay/v1` line protocol on stdin/stdout through the vendored kit shim (`vendor/makefun_bars.py`): it receives a `hello` handshake, then one batch of hourly bars at a time, and answers each batch with a reply carrying its buy/sell orders. Orders decided on a batch fill at the next bar's open. No network, no secrets, no randomness — fully deterministic, so the two grading runs produce identical action logs.

## Run

Smoke-test against the kit's dev dataset (feeds the bot a hello plus real bars and prints its replies):

```bash
python3 main.py < hello_and_bars.jsonl
```

Grade locally with the kit (needs Docker):

```bash
node cli/makefun.mjs grade-local --kit . --bot ~/workspace/makefun/tiny-bot-sol-25nov26 --driver docker
```

## License

MIT — see [LICENSE](LICENSE).
