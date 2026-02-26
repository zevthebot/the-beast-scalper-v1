import MetaTrader5 as mt5

if not mt5.initialize():
    print("Failed to connect")
    exit()

positions = mt5.positions_get()
print(f"Total positions: {len(positions)}\n")

for p in positions:
    direction = "BUY" if p.type == 0 else "SELL"
    print(f"{p.symbol} | {direction} | Profit: {p.profit:.2f} EUR | Ticket: {p.ticket}")

print(f"\nTotal profit: {sum(p.profit for p in positions):.2f} EUR")
mt5.shutdown()
