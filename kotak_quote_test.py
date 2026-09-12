from broker.kotak_api import KotakBroker


CE_TOKEN = "47293"
PE_TOKEN = "47294"
EXCHANGE_SEGMENT = "nse_fo"


def main():
    print("=" * 70)
    print("JHA SMARTTRADER AI PRO")
    print("KOTAK NEO READ-ONLY OPTION LTP TEST")
    print("=" * 70)

    broker = KotakBroker()

    print("\nConnecting to Kotak Neo...")

    if not broker.connect():
        print("\n❌ Kotak Neo connection failed.")
        print("Check your .env credentials.")
        return

    print("✅ Kotak Neo connected.")

    print("\nRequesting NIFTY CE + PE quotes...")

    result = broker.get_option_quotes(
        ce_token=CE_TOKEN,
        pe_token=PE_TOKEN,
        exchange_segment=EXCHANGE_SEGMENT,
    )

    print("\nRAW QUOTE RESPONSE:")
    print(result)

    if not result.get("success"):
        print("\n❌ QUOTE ERROR")
        print(result.get("error"))
        return

    print("\n" + "=" * 70)
    print("✅ KOTAK QUOTE RESPONSE RECEIVED")
    print("=" * 70)

    data = result.get("data")

    print("\nDATA:")
    print(data)

    print("\n" + "=" * 70)
    print("IMPORTANT:")
    print("This test is READ-ONLY.")
    print("No BUY order was sent.")
    print("No SELL order was sent.")
    print("=" * 70)


if __name__ == "__main__":
    main()