import logging
from datetime import datetime


def generate_report(
    total_trades,
    winning_trades,
    losing_trades,
    net_profit,
    daily_pnl,
    monthly_pnl,
    open_positions,
    broker_status
):
    """
    Generates a structured, formatted performance and status report for the trading system.
    """
    try:
        # Safe numeric parsing
        t_trades = int(total_trades or 0)
        w_trades = int(winning_trades or 0)
        
        win_rate = 0.0
        if t_trades > 0:
            win_rate = round((w_trades / t_trades) * 100.0, 2)

        # Clean formatted timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
====================================
      TRADING SYSTEM REPORT
====================================

Date & Time       : {current_time}

Total Trades      : {t_trades}
Winning Trades    : {w_trades}
Losing Trades     : {int(losing_trades or 0)}
Win Rate          : {win_rate}%

Net Profit        : ₹{float(net_profit or 0.0):,.2f}
Daily P&L         : ₹{float(daily_pnl or 0.0):,.2f}
Monthly P&L       : ₹{float(monthly_pnl or 0.0):,.2f}

Open Positions    : {open_positions}
Broker Status     : {broker_status}

====================================
"""
        return report

    except Exception as e:
        logging.error(f"❌ Error generating trading report: {e}")
        return "❌ Error generating report due to invalid data formats."