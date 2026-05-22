import subprocess
import json
import os
import tempfile
import pandas as pd
from pathlib import Path


class BacktestResult:
    def __init__(self, data: dict):
        self.trades = pd.DataFrame(data["trades"])
        self.stats = data["stats"]
        self.equity_curve = pd.DataFrame(data["equity_curve"])

        if not self.trades.empty and "entry_time" in self.trades.columns:
            self.trades["entry_time"] = pd.to_datetime(self.trades["entry_time"], unit="s")
            self.trades["exit_time"] = pd.to_datetime(self.trades["exit_time"], unit="s")

        if not self.equity_curve.empty and "timestamp" in self.equity_curve.columns:
            self.equity_curve["timestamp"] = pd.to_datetime(
                self.equity_curve["timestamp"], unit="s"
            )

    def summary(self):
        s = self.stats
        print("=" * 50)
        print("BACKTEST SUMMARY")
        print("=" * 50)
        print(f"  Initial Capital:  ${s['initial_capital']:,.2f}")
        print(f"  Final Equity:     ${s['final_equity']:,.2f}")
        print(f"  Total Return:     ${s['total_return']:+,.2f} ({s['total_return_pct']:+.2f}%)")
        print(f"  Max Drawdown:     ${s['max_drawdown']:,.2f} ({s['max_drawdown_pct']:.2f}%)")
        print(f"  Volatility:       {s['volatility']*100:.2f}%/bar")
        print(f"  Sharpe Ratio:     {s['sharpe_ratio']:.2f}")
        print(f"  Sortino Ratio:    {s['sortino_ratio']:.2f}")
        print(f"  Calmar Ratio:     {s['calmar_ratio']:.2f}")
        print("-" * 50)
        print(f"  Total Trades:     {s['total_trades']}")
        print(f"  Win Rate:         {s['win_rate']*100:.1f}%")
        print(f"  Profit Factor:    {s['profit_factor']:.2f}")
        print(f"  Expectancy:       ${s['expectancy']:+.2f} ({s['expectancy_pct']:+.2f}%)")
        print(f"  Avg Win:          ${s['avg_win']:+,.2f}")
        print(f"  Avg Loss:         ${s['avg_loss']:+,.2f}")
        print(f"  Largest Win:      ${s['largest_win']:+,.2f}")
        print(f"  Largest Loss:     ${s['largest_loss']:+,.2f}")
        print(f"  Avg Holding:      {s['avg_holding_period']:.1f} bars")
        print(f"  Max Cons Wins:    {s['max_consecutive_wins']}")
        print(f"  Max Cons Losses:  {s['max_consecutive_losses']}")
        print("=" * 50)


def run(
    df: pd.DataFrame,
    signal_col: str = "signal",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    tp_col: str = "tp_price",
    sl_col: str = "sl_price",
    units_col: str = "units",
    timestamp_col: str | None = None,
    initial_capital: float = 10_000.0,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    engine_path: str | None = None,
) -> BacktestResult:
    if engine_path is None:
        engine_path = (
            Path(__file__).parent.parent
            / "target"
            / "x86_64-unknown-linux-musl"
            / "release"
            / "backtest_engine"
        )

    if not os.path.exists(engine_path):
        raise FileNotFoundError(
            f"Rust engine not found at {engine_path}. Build it first with:\n"
            f"  cd {Path(__file__).parent.parent} && cargo build --release"
        )

    if timestamp_col is None:
        df = df.reset_index()
        timestamp_col = "index"

    cols = [timestamp_col, open_col, high_col, low_col, close_col, volume_col,
            signal_col, tp_col, sl_col, units_col]
    csv_df = df[cols].copy()

    if pd.api.types.is_datetime64_any_dtype(csv_df[timestamp_col]):
        csv_df[timestamp_col] = csv_df[timestamp_col].astype("datetime64[s]").astype("int64")
    elif hasattr(pd.api.types, 'is_timedelta64_any_dtype') and pd.api.types.is_timedelta64_any_dtype(csv_df[timestamp_col]):
        csv_df[timestamp_col] = csv_df[timestamp_col].astype("timedelta64[s]").astype("int64")

    csv_str = csv_df.to_csv(index=False)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        f.write(csv_str)
        csv_path = f.name

    try:
        proc = subprocess.run(
            [
                str(engine_path),
                csv_path,
                "--capital", str(initial_capital),
                "--commission", str(commission_pct),
                "--slippage", str(slippage_pct),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"Engine failed (code {proc.returncode}): {proc.stderr}"
            )

        data = json.loads(proc.stdout)
        return BacktestResult(data)

    finally:
        os.unlink(csv_path)
