# Deposit Bot

Receives a deposit POST request with three fields, renders them onto the
AIDEFI `Deposit.png` template with Pillow, and posts the finished image to the
Telegram channel **@aidefiofficially** (https://t.me/aidefiofficially) using a bot.

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Create a bot with [@BotFather](https://t.me/BotFather) and copy its token.

3. Add the bot to the channel `@aidefiofficially` **as an administrator** with
   permission to post messages. (A bot can only post to a channel/group it
   administers — it cannot post to a `t.me` URL directly.)

4. Set environment variables:

   Windows PowerShell:
   ```powershell
   $env:TELEGRAM_BOT_TOKEN = "123456:ABC-your-token"
   $env:TELEGRAM_CHAT_ID   = "@aidefiofficially"
   ```

   Linux/macOS:
   ```bash
   export TELEGRAM_BOT_TOKEN="123456:ABC-your-token"
   export TELEGRAM_CHAT_ID="@aidefiofficially"
   ```

5. Run the service:

   ```
   python app.py
   ```

   It listens on `http://0.0.0.0:5005` by default (override with `PORT`).

## API

### `POST /deposit`

JSON body (or form-encoded). Accepted field names:

| Field   | Accepted keys                                                        |
|---------|----------------------------------------------------------------------|
| Amount  | `amount`, `value`, `amt`                                             |
| Address | `address`, `user_address`, `userAddress`, `wallet`, `walletAddress` |
| Hash    | `hash`, `txHash`, `tx_hash`, `transactionHash`                      |

Example:

```bash
curl -X POST http://localhost:5005/deposit \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "1,500 USDT",
    "address": "0x65bb8da590f0C049c632f1743942734A39aBbe5F",
    "txHash": "0x9f2c1a4b7e8d3f6a0c5b2e9d1f4a7c8b3e6d9f2a1c4b7e8d3f6a0c5b2e9d1f4a"
  }'
```

Success response:

```json
{ "ok": true, "message": "deposit image sent to Telegram", "telegram_message_id": 123 }
```

### `GET /health`

Returns `{ "status": "ok" }`.

## Files

- `app.py` — Flask service and `/deposit` endpoint.
- `image_filler.py` — Pillow rendering onto `assets/Deposit.png`.
- `telegram_client.py` — Telegram Bot API `sendPhoto` wrapper.
- `assets/Deposit.png` — the template image.
- `fonts/` — bundled fonts so rendering works on any OS.
