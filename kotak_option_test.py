import os

from decouple import config
from neo_api_client import NeoAPI


consumer_key = config(
    "KOTAK_CONSUMER_KEY",
    default="",
)

if not consumer_key:
    raise RuntimeError(
        "KOTAK_CONSUMER_KEY is not configured."
    )


neo = NeoAPI(
    consumer_key=consumer_key,
    environment="prod",
)

print("=" * 70)
print("KOTAK NEO OPTION CONTRACT TEST")
print("=" * 70)

print("\n1. NSE F&O segment:")
print("   nse_fo")

print("\n2. Searching NIFTY option contracts...")

result = neo.search_scrip(
    exchange_segment="nse_fo",
    symbol="NIFTY",
    option_type="CE,PE",
    ignore_50multiple=False,
)

print("\nRAW RESPONSE:")
print(result)

print("\nRESPONSE TYPE:")
print(type(result))

if isinstance(result, dict):
    print("\nRESPONSE KEYS:")
    print(list(result.keys()))

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)

