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

    win_rate = 0

    if total_trades > 0:
        win_rate = round(
            (winning_trades / total_trades) * 100,
            2
        )

    report = f"""
====================================
      TRADING REPORT
====================================

Date: {datetime.now()}

Total Trades      : {total_trades}
Winning Trades    : {winning_trades}
Losing Trades     : {losing_trades}
Win Rate          : {win_rate}%

Net Profit        : ₹{net_profit}
Daily P&L         : ₹{daily_pnl}
Monthly P&L       : ₹{monthly_pnl}

Open Positions    : {open_positions}
Broker Status     : {broker_status}

====================================
"""

    return report
