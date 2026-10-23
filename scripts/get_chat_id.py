#!/usr/bin/env python3
"""
Helper script to discover your Telegram Chat ID.
Polls getUpdates from Telegram Bot API and captures your ID when you send a message.
Automatically updates your local .env file.

Usage:
    python -m scripts.get_chat_id
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.bot.client import TelegramClient, TelegramAPIError
from src.bot.config import load_config, save_chat_id_to_env


def main() -> None:
    config = load_config()
    if not config.bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not configured in .env!")
        print("Please set your bot token in .env before running this script.")
        sys.exit(1)

    client = TelegramClient(config.bot_token)
    try:
        me = client.get_me()
        bot_username = me.get("username", "your bot")
    except TelegramAPIError as e:
        print(f"❌ Failed to connect to Telegram Bot API: {e}")
        sys.exit(1)

    print("=" * 60)
    print(f"🤖 Connected to Telegram Bot: @{bot_username}")
    print("=" * 60)
    print(f"\n👉 Open Telegram, search for @{bot_username} (or visit https://t.me/{bot_username})")
    print("👉 Tap START or send any message (e.g. 'hello')...\n")
    print("Listening for incoming messages (press Ctrl+C to cancel)...")

    offset = None
    # First, flush old updates
    try:
        old_updates = client.get_updates(timeout=1)
        if old_updates:
            offset = old_updates[-1]["update_id"] + 1
    except Exception:
        pass

    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=5)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message") or update.get("channel_post")
                if msg:
                    chat = msg.get("chat", {})
                    chat_id = chat.get("id")
                    from_user = msg.get("from", {})
                    name = from_user.get("first_name", "User")
                    username = from_user.get("username", "")
                    user_tag = f" (@{username})" if username else ""

                    is_channel = chat.get("type") == "channel" or "channel_post" in update
                    chat_title = chat.get("title") or (f"{name}{user_tag}")

                    print("\n" + "🎉 " + "=" * 50)
                    if is_channel:
                        print(f"📢 Channel post detected from: {chat_title}")
                        print(f"🔑 Your Telegram Channel ID is: {chat_id}")
                        print("=" * 54)
                        from src.bot.config import save_channel_id_to_env
                        save_channel_id_to_env(chat_id)
                        print(f'💾 Automatically saved TELEGRAM_CHANNEL_ID="{chat_id}" to .env')
                    else:
                        print(f"✅ Private message received from: {chat_title}")
                        print(f"🔑 Your Telegram Chat ID is: {chat_id}")
                        print("=" * 54)
                        save_chat_id_to_env(chat_id)
                        print(f'💾 Automatically saved TELEGRAM_CHAT_ID="{chat_id}" to .env')

                        # Send confirmation message back to user on Telegram
                        try:
                            client.send_message(
                                chat_id,
                                f"🎉 <b>Journal Bot Connected!</b>\n\n"
                                f"Hello <b>{name}</b>! Your Chat ID (<code>{chat_id}</code>) has been successfully saved.\n\n"
                                f"Try sending <code>/start</code> or <code>/otd</code> to explore your journal archive!"
                            )
                            print("📬 Sent confirmation message to your Telegram!")
                        except Exception as e:
                            print(f"⚠️ Could not send confirmation reply: {e}")

                    print("\nAll done! You can now run:")
                    print("  - Daily Push:   python -m scripts.send_daily_otd")
                    print("  - Live Bot:     python -m scripts.run_bot")
                    return

            time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")
            return
        except Exception as e:
            print(f"⚠️ Error polling updates: {e}. Retrying in 3s...")
            time.sleep(3)


if __name__ == "__main__":
    main()
