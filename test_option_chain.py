from option_chain import get_option_chain

data = get_option_chain("NIFTY")

print("================================")
print(type(data))
print(data)
print("================================")