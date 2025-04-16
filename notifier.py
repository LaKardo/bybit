import asyncio
import telegram
import config
from datetime import datetime
class TelegramNotifier:
    def __init__(self, token=None, chat_id=None, logger=None):
        self.token = token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID
        self.logger = logger
        self.bot = None
        if self.token and self.chat_id and self.token != "your_telegram_bot_token_here":
            try:
                self.bot = telegram.Bot(token=self.token)
                if self.logger:
                    self.logger.info("Telegram notifier initialized")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to initialize Telegram bot: {e}")
                self.bot = None
        else:
            if self.logger:
                self.logger.warning("Telegram notifier not initialized: missing token or chat_id")
    async def _send_message_async(self, message):
        if not self.bot:
            if self.logger:
                self.logger.warning("Telegram bot not initialized, can't send message")
            return
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=telegram.constants.ParseMode.MARKDOWN
            )
            if self.logger:
                self.logger.debug(f"Telegram notification sent: {message[:50]}...")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to send Telegram notification: {e}")
    def send_message(self, message):
        if not self.bot:
            if self.logger:
                self.logger.warning("Telegram bot not initialized, can't send message")
            return
        asyncio.run(self._send_message_async(message))
    def notify_trade_entry(self, symbol, side, quantity, price, sl, tp):
        direction = "LONG 🟢" if side.upper() == "BUY" else "SHORT 🔴"
        risk_reward = abs(tp - price) / abs(price - sl) if sl and tp else "N/A"
        message = f"*NEW TRADE: {direction}*\n\n" \
                 f"*Symbol:* {symbol}\n" \
                 f"*Quantity:* {quantity}\n" \
                 f"*Entry Price:* {price}\n" \
                 f"*Stop Loss:* {sl} ({abs(sl - price) / price * 100:.2f}%)\n" \
                 f"*Take Profit:* {tp} ({abs(tp - price) / price * 100:.2f}%)\n" \
                 f"*Risk/Reward:* 1:{risk_reward:.2f}\n" \
                 f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_message(message)
    def notify_trade_exit(self, symbol, side, quantity, entry_price, exit_price, pnl, exit_reason):
        direction = "LONG 🟢" if side.upper() == "BUY" else "SHORT 🔴"
        pnl_percent = pnl / (entry_price * quantity) * 100
        emoji = "✅" if pnl > 0 else "❌"
        message = f"*CLOSED TRADE: {direction} {emoji}*\n\n" \
                 f"*Symbol:* {symbol}\n" \
                 f"*Quantity:* {quantity}\n" \
                 f"*Entry Price:* {entry_price}\n" \
                 f"*Exit Price:* {exit_price}\n" \
                 f"*PnL:* {pnl:.2f} USDT ({pnl_percent:.2f}%)\n" \
                 f"*Exit Reason:* {exit_reason}\n" \
                 f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_message(message)
    def notify_error(self, error_message):
        message = f"*⚠️ ERROR ⚠️*\n\n" \
                 f"{error_message}\n" \
                 f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        self.send_message(message)
    def notify_bot_status(self, status, additional_info=None):
        message = f"*BOT STATUS: {status}*\n" \
                 f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        if additional_info:
            message += f"\n\n{additional_info}"
        self.send_message(message)
