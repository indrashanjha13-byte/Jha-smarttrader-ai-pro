import logging


def calculate_pcr(option_chain, target_expiry=None):
    """
    Calculates Put-Call Ratio (PCR) and generates market sentiment signal 
    safely from NSE/Broker option chain structure.
    """
    try:
        if not isinstance(option_chain, dict):
            return {
                "PCR": 0.0,
                "Signal": "Invalid Data Format",
                "CE_OI": 0,
                "PE_OI": 0
            }

        # Check records
        if "records" not in option_chain:
            return {
                "PCR": 0.0,
                "Signal": "No Records Found",
                "Keys": list(option_chain.keys())
            }

        total_ce_oi = 0
        total_pe_oi = 0

        records_container = option_chain["records"]
        
        # If expiry list is provided in records, filter by nearest/target expiry if needed
        expiry_dates = records_container.get("expiryDates", [])
        active_expiry = target_expiry if target_expiry else (expiry_dates[0] if expiry_dates else None)

        rows = records_container.get("data", [])

        for row in rows:
            if not isinstance(row, dict):
                continue

            # Optional Expiry Filtering if data supports expiry-wise breakdown
            if active_expiry and row.get("expiryDate") and row.get("expiryDate") != active_expiry:
                continue

            ce = row.get("CE")
            pe = row.get("PE")

            if isinstance(ce, dict):
                total_ce_oi += int(ce.get("openInterest", 0) or 0)

            if isinstance(pe, dict):
                total_pe_oi += int(pe.get("openInterest", 0) or 0)

        # Zero Division Protection
        if total_ce_oi == 0:
            logging.warning("⚠️ Total CE Open Interest is zero. Cannot compute valid PCR.")
            return {
                "PCR": 0.0,
                "Signal": "NO LIQUIDITY / DATA",
                "CE_OI": 0,
                "PE_OI": total_pe_oi
            }

        pcr = round(float(total_pe_oi) / float(total_ce_oi), 2)

        # Standard Market PCR Interpretation Rules
        if pcr >= 1.25:
            signal = "🟢 Bullish (High Put Writing)"
        elif pcr <= 0.75:
            signal = "🔴 Bearish (High Call Writing)"
        else:
            signal = "🟡 Neutral (Consolidation Zone)"

        return {
            "PCR": pcr,
            "Signal": signal,
            "CE_OI": total_ce_oi,
            "PE_OI": total_pe_oi,
            "Expiry": active_expiry
        }

    except Exception as e:
        logging.error(f"❌ Error calculating PCR: {e}")
        return {
            "PCR": 0.0,
            "Signal": f"Error: {str(e)}",
            "CE_OI": 0,
            "PE_OI": 0
        }