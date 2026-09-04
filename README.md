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

| Field      | Accepted keys                                                        |
|------------|----------------------------------------------------------------------|
| Amount     | `amount`, `value`, `amt`                                            |
| Address    | `address`, `user_address`, `userAddress`, `wallet`, `walletAddress` |
| Hash       | `hash`, `txHash`, `tx_hash`, `transactionHash`                     |
| From where | `from_where`, `fromWhere`, `source` (optional, defaults to `website`) |

Every request is recorded in the deposits database (see below), including the
`from_where` source and whether the Telegram post succeeded.

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

### `GET /deposits`

Returns stored deposits, newest first. Optional query params:

| Param        | Meaning                                  |
|--------------|------------------------------------------|
| `limit`      | max rows (default 100, capped at 1000)   |
| `offset`     | pagination offset                        |
| `from_where` | filter by source, e.g. `website`/`script`|
| `address`    | filter by user address                   |

Example: `GET /deposits?from_where=script&limit=20`

```json
{
  "ok": true,
  "total": 42,
  "count": 20,
  "deposits": [
    {
      "id": 42,
      "amount": "1,000",
      "address": "0x...",
      "tx_hash": "0x...",
      "from_where": "website",
      "status": "sent",
      "telegram_message_id": 123,
      "error": null,
      "created_at": "2026-09-04T21:30:03+00:00"
    }
  ]
}
```

### `GET /health`

Returns `{ "status": "ok" }`.

## Database

Every deposit is stored in a `deposits` table with columns: `id`, `amount`,
`address`, `tx_hash`, `from_where`, `status` (`sent` / `telegram_error` /
`error`), `telegram_message_id`, `error`, `created_at`.

The backend is chosen automatically:

- **PostgreSQL** when `DATABASE_URL` is set. Use this on Render — its filesystem
  is ephemeral, so a SQLite file would be wiped on every redeploy. Create a free
  Render PostgreSQL instance and set its `DATABASE_URL` env var on the service.
- **SQLite** otherwise (local dev). Stored at `deposits.db` (override with
  `SQLITE_PATH`). This file is gitignored.

The table is created automatically on startup.

## Files

- `app.py` — Flask service and `/deposit` endpoint.
- `image_filler.py` — Pillow rendering onto `assets/Deposit.png`.
- `telegram_client.py` — Telegram Bot API `sendPhoto` wrapper.
- `assets/Deposit.png` — the template image.
- `fonts/` — bundled fonts so rendering works on any OS.
