mod engine;
mod stats;
mod types;

use crate::engine::run_backtest;
use crate::types::*;
use std::io::{self, Read};

fn parse_bar(timestamp: i64, record: &csv::StringRecord) -> Result<Bar, String> {
    let parse_f = |idx: usize| -> Result<f64, String> {
        record
            .get(idx)
            .ok_or_else(|| format!("missing column {}", idx))?
            .parse::<f64>()
            .map_err(|e| format!("parse error at column {}: {}", idx, e))
    };

    Ok(Bar {
        timestamp,
        open: parse_f(1)?,
        high: parse_f(2)?,
        low: parse_f(3)?,
        close: parse_f(4)?,
        volume: parse_f(5)?,
        signal: parse_f(6)?,
        tp_price: parse_f(7)?,
        sl_price: parse_f(8)?,
        units: parse_f(9)?,
    })
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut idx = 0;

    let input_source: Box<dyn Read> = if args.first().map_or(true, |a| a.starts_with("--")) {
        Box::new(io::stdin())
    } else {
        let path = &args[0];
        idx = 1;
        if path == "--" || path == "-" {
            Box::new(io::stdin())
        } else {
            Box::new(std::fs::File::open(&path).unwrap_or_else(|e| {
                eprintln!("Error opening file {}: {}", path, e);
                std::process::exit(1);
            }))
        }
    };

    let mut config = EngineConfig::default();
    while idx < args.len() {
        match args[idx].as_str() {
            "--capital" => {
                idx += 1;
                if idx < args.len() {
                    config.initial_capital = args[idx].parse().unwrap_or(10_000.0);
                }
            }
            "--commission" => {
                idx += 1;
                if idx < args.len() {
                    config.commission_pct = args[idx].parse().unwrap_or(0.001);
                }
            }
            "--slippage" => {
                idx += 1;
                if idx < args.len() {
                    config.slippage_pct = args[idx].parse().unwrap_or(0.0005);
                }
            }
            _ => {}
        }
        idx += 1;
    }

    let mut reader = csv::ReaderBuilder::new()
        .has_headers(true)
        .flexible(true)
        .from_reader(input_source);

    let mut bars: Vec<Bar> = Vec::new();
    for result in reader.records() {
        let record = result.unwrap_or_else(|e| {
            eprintln!("CSV parse error: {}", e);
            std::process::exit(1);
        });

        let ts_raw = record.get(0).unwrap_or("0");
        let timestamp: i64 = ts_raw.parse().unwrap_or_else(|_| {
            eprintln!("Error: non-numeric timestamp '{}' at line {}. Use Unix timestamps (seconds since epoch).", ts_raw, bars.len() + 2);
            std::process::exit(1);
        });

        match parse_bar(timestamp, &record) {
            Ok(bar) => bars.push(bar),
            Err(e) => {
                eprintln!("Warning: {} on line {}", e, bars.len() + 2);
            }
        }
    }

    if bars.is_empty() {
        eprintln!("No valid bars found in input");
        std::process::exit(1);
    }

    let result = run_backtest(&bars, &config);

    use serde::Serialize;

    #[derive(Serialize)]
    struct Output {
        trades: Vec<Trade>,
        stats: stats::BacktestStats,
        equity_curve: Vec<EquityPoint>,
    }

    let output = Output {
        trades: result.trades,
        stats: result.stats,
        equity_curve: result.equity_curve,
    };

    let json = serde_json::to_string_pretty(&output).unwrap();
    println!("{}", json);
}
