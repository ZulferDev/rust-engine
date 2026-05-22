use crate::types::*;
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct BacktestStats {
    // General
    pub initial_capital: f64,
    pub final_equity: f64,
    pub total_return: f64,
    pub total_return_pct: f64,

    // Risk
    pub max_drawdown: f64,
    pub max_drawdown_pct: f64,
    pub volatility: f64,

    // Trade stats
    pub total_trades: u64,
    pub winning_trades: u64,
    pub losing_trades: u64,
    pub breakeven_trades: u64,
    pub win_rate: f64,
    pub avg_win: f64,
    pub avg_loss: f64,
    pub largest_win: f64,
    pub largest_loss: f64,
    pub avg_win_pct: f64,
    pub avg_loss_pct: f64,
    pub profit_factor: f64,
    pub expectancy: f64,
    pub expectancy_pct: f64,
    pub avg_holding_period: f64,
    pub max_holding_period: u64,
    pub min_holding_period: u64,
    pub avg_trade_pnl: f64,

    // Ratios
    pub sharpe_ratio: f64,
    pub sortino_ratio: f64,
    pub calmar_ratio: f64,

    // Consecutive
    pub max_consecutive_wins: u64,
    pub max_consecutive_losses: u64,
}

impl BacktestStats {
    pub fn calculate(
        bars: &[Bar],
        trades: &[Trade],
        equity_curve: &[EquityPoint],
        config: &EngineConfig,
    ) -> Self {
        let total_trades = trades.len() as u64;

        if total_trades == 0 {
            return Self::empty(config, equity_curve);
        }

        let winning: Vec<&Trade> = trades.iter().filter(|t| t.pnl > 0.0).collect();
        let losing: Vec<&Trade> = trades.iter().filter(|t| t.pnl < 0.0).collect();
        let breakeven: Vec<&Trade> = trades.iter().filter(|t| t.pnl == 0.0).collect();
        let winning_trades = winning.len() as u64;
        let losing_trades = losing.len() as u64;
        let breakeven_trades = breakeven.len() as u64;

        let win_rate = if total_trades > 0 {
            winning_trades as f64 / total_trades as f64
        } else {
            0.0
        };

        let avg_win = if !winning.is_empty() {
            winning.iter().map(|t| t.pnl).sum::<f64>() / winning.len() as f64
        } else {
            0.0
        };
        let avg_loss = if !losing.is_empty() {
            losing.iter().map(|t| t.pnl).sum::<f64>() / losing.len() as f64
        } else {
            0.0
        };

        let largest_win = if winning.is_empty() {
            0.0
        } else {
            winning.iter().map(|t| t.pnl).fold(f64::NEG_INFINITY, f64::max)
        };
        let largest_loss = if losing.is_empty() {
            0.0
        } else {
            losing.iter().map(|t| t.pnl).fold(f64::INFINITY, f64::min)
        };

        let avg_win_pct = if !winning.is_empty() {
            winning.iter().map(|t| t.pnl_pct).sum::<f64>() / winning.len() as f64
        } else {
            0.0
        };
        let avg_loss_pct = if !losing.is_empty() {
            losing.iter().map(|t| t.pnl_pct).sum::<f64>() / losing.len() as f64
        } else {
            0.0
        };

        let gross_profit: f64 = winning.iter().map(|t| t.pnl).sum();
        let gross_loss: f64 = losing.iter().map(|t| t.pnl).sum();
        let profit_factor = if gross_loss.abs() > 1e-10 {
            gross_profit / gross_loss.abs()
        } else if gross_profit > 0.0 {
            999.0
        } else {
            0.0
        };

        let total_pnl: f64 = trades.iter().map(|t| t.pnl).sum();
        let expectancy = if total_trades > 0 {
            total_pnl / total_trades as f64
        } else {
            0.0
        };

        let total_pnl_pct: f64 = trades.iter().map(|t| t.pnl_pct).sum();
        let expectancy_pct = if total_trades > 0 {
            total_pnl_pct / total_trades as f64
        } else {
            0.0
        };

        let final_equity = if let Some(last) = equity_curve.last() {
            last.equity
        } else {
            config.initial_capital
        };
        let total_return = final_equity - config.initial_capital;
        let total_return_pct = if config.initial_capital > 0.0 {
            (total_return / config.initial_capital) * 100.0
        } else {
            0.0
        };

        let max_dd = equity_curve
            .iter()
            .map(|e| e.drawdown)
            .fold(0.0, f64::max);
        let max_dd_pct = equity_curve
            .iter()
            .map(|e| e.drawdown_pct)
            .fold(0.0, f64::max);

        let avg_holding = trades.iter().map(|t| t.holding_period).sum::<u64>() as f64
            / total_trades as f64;
        let max_holding = trades.iter().map(|t| t.holding_period).max().unwrap_or(0);
        let min_holding = trades.iter().map(|t| t.holding_period).min().unwrap_or(0);

        let bar_returns: Vec<f64> = equity_curve
            .windows(2)
            .map(|w| (w[1].equity - w[0].equity) / w[0].equity)
            .filter(|r| r.is_finite())
            .collect();

        let avg_return = if !bar_returns.is_empty() {
            bar_returns.iter().sum::<f64>() / bar_returns.len() as f64
        } else {
            0.0
        };

        let variance = if bar_returns.len() > 1 {
            bar_returns
                .iter()
                .map(|r| (r - avg_return).powi(2))
                .sum::<f64>()
                / (bar_returns.len() - 1) as f64
        } else {
            0.0
        };
        let volatility = variance.sqrt();

        let bars_per_year = if bars.len() > 1 {
            let total_bars = bars.len();
            let last_ts = bars[total_bars - 1].timestamp;
            let first_ts = bars[0].timestamp;
            if last_ts > first_ts {
                let duration_years = (last_ts - first_ts) as f64 / 86_400.0 / 365.25;
                if duration_years > 0.0 {
                    total_bars as f64 / duration_years
                } else {
                    252.0
                }
            } else {
                252.0
            }
        } else {
            252.0
        };
        let annual_factor = bars_per_year.sqrt();

        let sharpe_ratio = if volatility > 0.0 {
            avg_return * annual_factor / volatility
        } else {
            0.0
        };

        let return_target = 0.0;
        let downside_sq_sum: f64 = bar_returns
            .iter()
            .map(|r| (r - return_target).min(0.0).powi(2))
            .sum();
        let downside_dev = if !bar_returns.is_empty() {
            (downside_sq_sum / bar_returns.len() as f64).sqrt()
        } else {
            0.0
        };
        let sortino_ratio = if downside_dev > 0.0 {
            avg_return * annual_factor / downside_dev
        } else {
            if total_return > 0.0 { 999.0 } else { 0.0 }
        };

        let annualized_return_pct = if bars_per_year > 0.0 && !bar_returns.is_empty() {
            (avg_return * bars_per_year) * 100.0
        } else {
            0.0
        };
        let calmar_ratio = if max_dd_pct > 0.0 && annualized_return_pct > 0.0 {
            annualized_return_pct / max_dd_pct
        } else {
            if total_return > 0.0 { 999.0 } else { 0.0 }
        };

        let mut max_consecutive_wins: u64 = 0;
        let mut max_consecutive_losses: u64 = 0;
        let mut cur_wins: u64 = 0;
        let mut cur_losses: u64 = 0;
        for t in trades {
            if t.pnl > 0.0 {
                cur_wins += 1;
                cur_losses = 0;
                if cur_wins > max_consecutive_wins {
                    max_consecutive_wins = cur_wins;
                }
            } else if t.pnl < 0.0 {
                cur_losses += 1;
                cur_wins = 0;
                if cur_losses > max_consecutive_losses {
                    max_consecutive_losses = cur_losses;
                }
            }
        }

        let avg_trade_pnl = if total_trades > 0 {
            total_pnl / total_trades as f64
        } else {
            0.0
        };

        Self {
            initial_capital: config.initial_capital,
            final_equity,
            total_return,
            total_return_pct,
            max_drawdown: max_dd,
            max_drawdown_pct: max_dd_pct,
            volatility,
            total_trades,
            winning_trades,
            losing_trades,
            breakeven_trades,
            win_rate,
            avg_win,
            avg_loss,
            largest_win,
            largest_loss,
            avg_win_pct,
            avg_loss_pct,
            profit_factor,
            expectancy,
            expectancy_pct,
            avg_holding_period: avg_holding,
            max_holding_period: max_holding,
            min_holding_period: min_holding,
            avg_trade_pnl,
            sharpe_ratio,
            sortino_ratio,
            calmar_ratio,
            max_consecutive_wins,
            max_consecutive_losses,
        }
    }

    fn empty(config: &EngineConfig, equity_curve: &[EquityPoint]) -> Self {
        let final_equity = if let Some(last) = equity_curve.last() {
            last.equity
        } else {
            config.initial_capital
        };
        let total_return = final_equity - config.initial_capital;
        let total_return_pct = if config.initial_capital > 0.0 {
            (total_return / config.initial_capital) * 100.0
        } else {
            0.0
        };
        let max_dd_pct = equity_curve
            .iter()
            .map(|e| e.drawdown_pct)
            .fold(0.0, f64::max);

        Self {
            initial_capital: config.initial_capital,
            final_equity,
            total_return,
            total_return_pct,
            max_drawdown: 0.0,
            max_drawdown_pct: max_dd_pct,
            volatility: 0.0,
            total_trades: 0,
            winning_trades: 0,
            losing_trades: 0,
            breakeven_trades: 0,
            win_rate: 0.0,
            avg_win: 0.0,
            avg_loss: 0.0,
            largest_win: 0.0,
            largest_loss: 0.0,
            avg_win_pct: 0.0,
            avg_loss_pct: 0.0,
            profit_factor: 0.0,
            expectancy: 0.0,
            expectancy_pct: 0.0,
            avg_holding_period: 0.0,
            max_holding_period: 0,
            min_holding_period: 0,
            avg_trade_pnl: 0.0,
            sharpe_ratio: 0.0,
            sortino_ratio: 0.0,
            calmar_ratio: 0.0,
            max_consecutive_wins: 0,
            max_consecutive_losses: 0,
        }
    }
}
