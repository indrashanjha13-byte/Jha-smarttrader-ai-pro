import logging
from option_chain import get_option_chain

def test_fetch_option_chain():
    """Test script to fetch and inspect Nifty Option Chain data."""
    print("==================================")
    print("Fetching Nifty Option Chain Data...")
    print("==================================")
    
    try:
        data = get_option_chain("NIFTY")
        
        print(f"Data Type: {type(data)}")
        
        if isinstance(data, (dict, list)) and len(data) > 0:
            print("Status: ✅ Option Chain fetched successfully.")
            # Print preview or first few entries depending on structure
            print(data if isinstance(data, dict) else data[:2])
        else:
            print("Status: ⚠️ Empty or invalid data received.")
            
    except Exception as e:
        logging.error(f"❌ Error fetching option chain: {e}")
        print(f"Status: ❌ Failed with error: {e}")
        
    print("==================================")

if __name__ == "__main__":
    test_fetch_option_chain()