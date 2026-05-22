import subprocess
import json
import os
import tempfile
import pandas as pd
from pathlib import Path
from .builder import get_engine_path


__all__ = ["BacktestResult", "run"]


class BacktestResult:
    """Hasil backtest: trades, equity curve, dan statistik."""

    def __init__(self, data: dict):
        self.trades = pd.DataFrame(data.get("trades", []))
        self.stats = data.get("stats", {})
        self.equity_curve = pd.DataFrame(data.get("equity_curve", []))

        if not self.trades.empty and "entry_time" in self.trades.columns:
            self.trades["entry_time"] = pd.to_datetime(
                self.trades["entry_time"], unit="s"
            )
            self.trades["exit_time"] = pd.to_datetime(
                self.trades["exit_time"], unit="s"
            )

        if not self.equity_curve.empty and "timestamp" in self.equity_curve.columns:
            self.equity_curve["timestamp"] = pd.to_datetime(
                self.equity_curve["timestamp"], unit="s"
            )

    def summary(self):
        s = self.stats
        print("=" * 50)
        print("BACKTEST SUMMARY")
        print("=" * 50)
        print(f"  Initial Capital:  ${s.get('initial_capital',0):,.2f}")
        print(f"  Final Equity:     ${s.get('final_equity',0):,.2f}")
        print(f"  Total Return:     ${s.get('total_return',0):+,.2f} ({s.get('total_return_pct',0):+.2f}%)")
        print(f"  Max Drawdown:     ${s.get('max_drawdown',0):,.2f} ({s.get('max_drawdown_pct',0):.2f}%)")
        print(f"  Volatility:       {s.get('volatility',0)*100:.2f}%/bar")
        print(f"  Sharpe Ratio:     {s.get('sharpe_ratio',0):.2f}")
        print(f"  Sortino Ratio:    {s.get('sortino_ratio',0):.2f}")
        print(f"  Calmar Ratio:     {s.get('calmar_ratio',0):.2f}")
        print("-" * 50)
        print(f"  Total Trades:     {s.get('total_trades',0)}")
        print(f"  Win / Loss / BE:  {s.get('winning_trades',0)} / {s.get('losing_trades',0)} / {s.get('breakeven_trades',0)}")
        print(f"  Win Rate:         {s.get('win_rate',0)*100:.1f}%")
        print(f"  Profit Factor:    {s.get('profit_factor',0):.2f}")
        print(f"  Expectancy:       ${s.get('expectancy',0):+,.2f}")
        print(f"  Avg Win:          ${s.get('avg_win',0):+,.2f}")
        print(f"  Avg Loss:         ${s.get('avg_loss',0):+,.2f}")
        print(f"  Avg Holding:      {s.get('avg_holding_period',0):.1f} bars")
        print(f"  Max Cons Wins:    {s.get('max_consecutive_wins',0)}")
        print(f"  Max Cons Losses:  {s.get('max_consecutive_losses',0)}")
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
    """
    Jalankan backtest.

    Parameters
    ----------
    df : pd.DataFrame
        Data OHLCV + signal + tp/sl + units.
    signal_col : str
        Nama kolom signal (1=Long, -1=Short, 0=no action).
    open_col, high_col, low_col, close_col, volume_col : str
        Nama kolom OHLCV.
    tp_col, sl_col : str
        Nama kolom take profit dan stop loss.
    units_col : str
        Nama kolom jumlah unit per trade.
    timestamp_col : str or None
        Nama kolom timestamp. None = pakai index.
    initial_capital : float
        Modal awal.
    commission_pct : float
        Komisi per transaksi (diterapkan 2x: entry+exit).
    slippage_pct : float
        Slippage pada entry price.
    engine_path : str or None
        Path ke Rust binary. None = auto-detect/build.

    Returns
    -------
    BacktestResult
    """
    if engine_path is None:
        engine_path = get_engine_path()

    if timestamp_col is None:
        df = df.reset_index()
        timestamp_col = "index"

    cols = [
        timestamp_col, open_col, high_col, low_col, close_col, volume_col,
        signal_col, tp_col, sl_col, units_col,
    ]
    csv_df = df[cols].copy()

    if pd.api.types.is_datetime64_any_dtype(csv_df[timestamp_col]):
        csv_df[timestamp_col] = csv_df[timestamp_col].astype("datetime64[s]").astype("int64")
    elif hasattr(pd.api.types, "is_timedelta64_any_dtype") and pd.api.types.is_timedelta64_any_dtype(csv_df[timestamp_col]):
        csv_df[timestamp_col] = csv_df[timestamp_col].astype("timedelta64[s]").astype("int64")

    csv_str = csv_df.to_csv(index=False)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
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
            raise RuntimeError(f"Engine failed (code {proc.returncode}): {proc.stderr}")

        data = json.loads(proc.stdout)
        return BacktestResult(data)

    finally:
        os.unlink(csv_path)
