"""
Telegram Notification Dispatcher for SharpBet Core.
Formats value bets into Markdown messages.
"""

import logging
from typing import Any

import requests

from unified_betting_core.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger("SharpBet.Telegram")


class TelegramNotifier:
    def __init__(
        self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID
    ):
        self.token = token
        self.chat_id = chat_id

    def send_report(self, bets: list[dict[str, Any]], bankroll: float) -> bool:
        """Sends formatted betting alert to Telegram."""
        if not bets:
            return False

        if "dummy" in self.token:
            logger.info("Telegram notification skipped (dummy token configured).")
            return False

        msg_lines = [
            "⚽ *SharpBet Core - Daily Value Bets Report*",
            f"💰 *Bankroll:* €{bankroll:,.2f}\n",
        ]

        for b in bets:
            msg_lines.append(
                f"🔥 *{b.get('match')}*\n"
                f"• Tip: `{str(b.get('bet_on')).upper()}` @ *{b.get('odds'):.2f}*\n"
                f"• Model: *{b.get('model_prob', 0) * 100:.1f}%* | Edge: *+{b.get('edge_pct', 0):.1f}%*\n"
                f"• Preporučeni ulog: *€{b.get('stake', 0):.2f}*\n"
                f"• Analiza: _{b.get('llm_comment', '')}_\n"
            )

        text = "\n".join(msg_lines)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        try:
            res = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=5,
            )
            return res.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"Telegram dispatch failed: {e}")
            return False
