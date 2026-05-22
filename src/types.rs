use serde::Serialize;

#[derive(Debug, Clone, Copy)]
pub struct Bar {
    pub timestamp: i64,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: f64,
    pub signal: f64,
    pub tp_price: f64,
    pub sl_price: f64,
    pub units: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub enum Direction {
    Long,
    Short,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize)]
pub enum ExitReason {
    TakeProfit,
    StopLoss,
}

#[derive(Debug, Clone, Serialize)]
pub struct Trade {
    pub entry_time: i64,
    pub exit_time: i64,
    pub direction: Direction,
    pub entry_price: f64,
    pub exit_price: f64,
    pub units: f64,
    pub pnl: f64,
    pub pnl_pct: f64,
    pub holding_period: u64,
    pub entry_idx: usize,
    pub exit_idx: usize,
    pub exit_reason: ExitReason,
    pub tp_price: f64,
    pub sl_price: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct EquityPoint {
    pub timestamp: i64,
    pub equity: f64,
    pub drawdown: f64,
    pub drawdown_pct: f64,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PositionState {
    Flat,
    Long {
        entry_price: f64,
        entry_idx: usize,
        units: f64,
        tp_price: f64,
        sl_price: f64,
        entry_equity: f64,
    },
    Short {
        entry_price: f64,
        entry_idx: usize,
        units: f64,
        tp_price: f64,
        sl_price: f64,
        entry_equity: f64,
    },
}

#[derive(Debug, Clone)]
pub struct EngineConfig {
    pub initial_capital: f64,
    pub commission_pct: f64,
    pub slippage_pct: f64,
}

impl Default for EngineConfig {
    fn default() -> Self {
        Self {
            initial_capital: 10_000.0,
            commission_pct: 0.001,
            slippage_pct: 0.0005,
        }
    }
}
