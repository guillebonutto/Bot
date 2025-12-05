"""
Remove emojis from auto_trainer.py to fix Windows encoding issues
"""

def remove_emojis():
    with open('auto_trainer.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace emojis with text
    replacements = {
        '✅': '[OK]',
        '⚠️': '[WARN]',
        '❌': '[ERROR]',
        '📂': '[INFO]',
        '🔧': '[INFO]',
        '📊': '[INFO]',
        '🤖': '[INFO]',
        '📈': '[INFO]',
        '🎉': '[SUCCESS]',
        '🔒': '[INFO]',
        '⏸️': '[SKIP]',
        '💾': '[INFO]',
        '🚀': '',
        '🎯': '',
        '💰': '[INFO]',
    }
    
    for emoji, text in replacements.items():
        content = content.replace(emoji, text)
    
    with open('auto_trainer.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Emojis removed from auto_trainer.py")

if __name__ == "__main__":
    remove_emojis()
