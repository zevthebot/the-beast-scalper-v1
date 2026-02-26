import re

path = r'C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all emoji characters (replace with text equivalents or nothing)
replacements = {
    '📊': '[REPORT]',
    '🛡️': '[PROTECT]',
    '🛡': '[PROTECT]',
    '📈': '[TRAIL]',
    '🚨': '[ALERT]',
    '✅': '[OK]',
    '❌': '[FAIL]',
    '⚠️': '[WARN]',
    '⚠': '[WARN]',
    '⏱️': '[TIMER]',
    '⏱': '[TIMER]',
    '🌅': '[RESET]',
    '🎉': '[WIN]',
    'ℹ️': '[INFO]',
    'ℹ': '[INFO]',
    '✓': '[OK]',
    '✗': '[FAIL]',
}

for emoji, text in replacements.items():
    content = content.replace(emoji, text)

# Also remove any remaining non-ASCII emoji-like chars
# Keep basic ASCII + common extended latin
content_clean = []
for char in content:
    if ord(char) < 0x10000:  # Keep BMP characters
        content_clean.append(char)
    else:
        content_clean.append('*')
content = ''.join(content_clean)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Fixed emoji in bot_controller.py")
