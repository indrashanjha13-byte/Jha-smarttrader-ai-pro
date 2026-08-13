# option_chain_ai.py

def calculate_pcr(option_chain):

    try:

        # Check records
        if "records" not in option_chain:
            return {
                "PCR": 0,
                "Signal": "No Records",
                "Keys": list(option_chain.keys())
            }

        total_ce_oi = 0
        total_pe_oi = 0

        records = option_chain["records"].get("data", [])

        for row in records:

            ce = row.get("CE")
            pe = row.get("PE")

            if ce:
                total_ce_oi += ce.get("openInterest", 0)

            if pe:
                total_pe_oi += pe.get("openInterest", 0)

        if total_ce_oi == 0:
            return {
                "PCR": 0,
                "Signal": "NO DATA"
            }

        pcr = round(total_pe_oi / total_ce_oi, 2)

        if pcr >= 1.20:
            signal = "🟢 Bullish"

        elif pcr <= 0.80:
            signal = "🔴 Bearish"

        else:
            signal = "🟡 Neutral"

        return {
            "PCR": pcr,
            "Signal": signal,
            "CE_OI": total_ce_oi,
            "PE_OI": total_pe_oi
        }

    except Exception as e:

        return {
            "PCR": 0,
            "Signal": f"Error: {e}"
        }
