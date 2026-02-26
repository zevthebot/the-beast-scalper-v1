import pytz
from datetime import datetime
prague = pytz.timezone('Europe/Prague')
now = datetime.now(prague)
print(f'Prague: {now.strftime("%Y-%m-%d %H:%M")}')
print(f'Hour: {now.hour}')
print(f'Date: {now.date()}')
if now.hour >= 0:
    print('Reset would have occurred today at 00:00 CET')
