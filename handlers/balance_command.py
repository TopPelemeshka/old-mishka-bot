# handlers/balance_command.py
from telegram import Update
from telegram.ext import ContextTypes
from balance import load_balances

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balances = load_balances()
    if not balances:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Баланс пока пуст."
        )
        return

    text = "💰 Баланс участников:\n\n"
    # Здесь ключи – строки с user_id, значение – словарь с name и balance
    for user_id, data in balances.items():
        name = data["name"]
        balance = data["balance"]
        text += f"{name}: {balance} 💵\n"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text
    )
