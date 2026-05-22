use crate::stats::BacktestStats;
use crate::types::*;

#[derive(Debug, Clone)]
pub struct BacktestResult {
    pub trades: Vec<Trade>,
    pub equity_curve: Vec<EquityPoint>,
    pub stats: BacktestStats,
}

type ExitInfo = (f64, Direction, f64, usize, f64, f64, f64, f64, ExitReason);

fn check_exit(state: &PositionState, bar: &Bar) -> Option<ExitInfo> {
    match *state {
        PositionState::Long {
            entry_price,
            entry_idx,
            units,
            tp_price,
            sl_price,
            entry_equity,
        } => {
            if bar.high >= tp_price {
                Some((tp_price, Direction::Long, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, ExitReason::TakeProfit))
            } else if bar.low <= sl_price {
                Some((sl_price, Direction::Long, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, ExitReason::StopLoss))
            } else {
                None
            }
        }
        PositionState::Short {
            entry_price,
            entry_idx,
            units,
            tp_price,
            sl_price,
            entry_equity,
        } => {
            if bar.low <= tp_price {
                Some((tp_price, Direction::Short, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, ExitReason::TakeProfit))
            } else if bar.high >= sl_price {
                Some((sl_price, Direction::Short, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, ExitReason::StopLoss))
            } else {
                None
            }
        }
        PositionState::Flat => None,
    }
}

fn close_trade(
    exit_price: f64,
    dir: Direction,
    entry_price: f64,
    entry_idx: usize,
    units: f64,
    tp_price: f64,
    sl_price: f64,
    entry_equity: f64,
    reason: ExitReason,
    i: usize,
    bar: &Bar,
    bars: &[Bar],
    config: &EngineConfig,
    trades: &mut Vec<Trade>,
    cash: &mut f64,
) {
    let notional = units * entry_price;
    let commission = notional * config.commission_pct;

    let raw_return = match dir {
        Direction::Long => (exit_price - entry_price) / entry_price,
        Direction::Short => (entry_price - exit_price) / entry_price,
    };

    let gross_pnl = raw_return * notional;
    let pnl = gross_pnl - 2.0 * commission;
    let pnl_pct = if entry_equity > 0.0 {
        pnl / entry_equity * 100.0
    } else {
        0.0
    };

    *cash += pnl;

    trades.push(Trade {
        entry_time: bars[entry_idx].timestamp,
        exit_time: bar.timestamp,
        direction: dir,
        entry_price,
        exit_price,
        units,
        pnl,
        pnl_pct,
        holding_period: (i - entry_idx) as u64,
        entry_idx,
        exit_idx: i,
        exit_reason: reason,
        tp_price,
        sl_price,
    });
}

pub fn run_backtest(bars: &[Bar], config: &EngineConfig) -> BacktestResult {
    let mut trades: Vec<Trade> = Vec::with_capacity(bars.len() / 10);
    let mut equity_curve: Vec<EquityPoint> = Vec::with_capacity(bars.len());

    let mut state: PositionState = PositionState::Flat;
    let mut cash = config.initial_capital;
    let mut peak_equity = config.initial_capital;

    for (i, bar) in bars.iter().enumerate() {
        // 1. Check TP/SL exit
        if let Some((exit_price, dir, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, reason)) = check_exit(&state, bar) {
            close_trade(exit_price, dir, entry_price, entry_idx, units, tp_price, sl_price, entry_equity, reason, i, bar, bars, config, &mut trades, &mut cash);
            state = PositionState::Flat;
        }

        // 2. Calculate equity (MTM if in position, else cash)
        let current_equity = match state {
            PositionState::Long {
                entry_price,
                units,
                ..
            } => {
                let notional = units * entry_price;
                let raw_pnl = (bar.close - entry_price) / entry_price;
                cash + raw_pnl * notional
            }
            PositionState::Short {
                entry_price,
                units,
                ..
            } => {
                let notional = units * entry_price;
                let raw_pnl = (entry_price - bar.close) / entry_price;
                cash + raw_pnl * notional
            }
            PositionState::Flat => cash,
        };

        if current_equity > peak_equity {
            peak_equity = current_equity;
        }
        let dd = peak_equity - current_equity;
        let dd_pct = if peak_equity > 0.0 {
            dd / peak_equity * 100.0
        } else {
            0.0
        };

        equity_curve.push(EquityPoint {
            timestamp: bar.timestamp,
            equity: current_equity,
            drawdown: dd,
            drawdown_pct: dd_pct,
        });

        // 3. Open new position if flat and signal matches
        if let PositionState::Flat = state {
            if bar.signal == 1.0 {
                let entry_price = bar.close * (1.0 + config.slippage_pct);
                let notional = bar.units * entry_price;
                if notional > cash {
                    continue;
                }
                state = PositionState::Long {
                    entry_price,
                    entry_idx: i,
                    units: bar.units,
                    tp_price: bar.tp_price,
                    sl_price: bar.sl_price,
                    entry_equity: cash,
                };
            } else if bar.signal == -1.0 {
                let entry_price = bar.close * (1.0 - config.slippage_pct);
                let notional = bar.units * entry_price;
                if notional > cash {
                    continue;
                }
                state = PositionState::Short {
                    entry_price,
                    entry_idx: i,
                    units: bar.units,
                    tp_price: bar.tp_price,
                    sl_price: bar.sl_price,
                    entry_equity: cash,
                };
            }
        }
    }

    let stats = BacktestStats::calculate(bars, &trades, &equity_curve, config);

    BacktestResult {
        trades,
        equity_curve,
        stats,
    }
}
