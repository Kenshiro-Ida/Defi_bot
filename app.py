"""Deposit bot service.

Receives a POST /deposit with three fields (amount, address, txHash),
fills the AIDEFI Deposit.png template using Pillow, and posts the image
to the Telegram channel @aidefiofficially via a bot.

Run:
    set TELEGRAM_BOT_TOKEN=123456:ABC...      (Windows PowerShell: $env:TELEGRAM_BOT_TOKEN="...")
    set TELEGRAM_CHAT_ID=@aidefiofficially
    python app.py
"""
import os

from flask import Flask, jsonify, request
from flask_cors import CORS

import db
from image_filler import fill_deposit_image
from telegram_client import TelegramError, send_photo

app = Flask(__name__)

# Create the deposits table on startup (Postgres if DATABASE_URL is set,
# otherwise a local SQLite file).
db.init_db()

# Values accepted for the "from_where" field; anything else is stored verbatim
# but normalized to lowercase. Defaults to "website".
DEFAULT_FROM_WHERE = "website"

# CORS: allow the frontend origin(s) to call /deposit from the browser.
# Set ALLOWED_ORIGINS as a comma-separated list (e.g.
# "https://aidefi.world,https://www.aidefi.world"); defaults to "*".
# Trailing slashes are stripped because a browser Origin header never has one
# (e.g. "https://www.aidefi.world"), and CORS origin matching is exact.
_origins_env = os.environ.get("ALLOWED_ORIGINS", "*").strip()
if _origins_env in ("", "*"):
    _origins = "*"
else:
    _origins = [o.strip().rstrip("/") for o in _origins_env.split(",") if o.strip()]
CORS(app, resources={
    r"/deposit": {"origins": _origins},
    r"/deposits": {"origins": _origins},
    r"/health": {"origins": _origins},
})

# Accept a few common key spellings for each field.
FIELD_ALIASES = {
    "amount": ["amount", "value", "amt"],
    "address": ["address", "user_address", "userAddress", "wallet", "walletAddress"],
    "hash": ["hash", "txHash", "tx_hash", "transactionHash", "transaction_hash", "txhash"],
}


def _extract(payload):
    values = {}
    missing = []
    for canonical, aliases in FIELD_ALIASES.items():
        found = None
        for a in aliases:
            if a in payload and str(payload[a]).strip() != "":
                found = str(payload[a]).strip()
                break
        if found is None:
            missing.append(canonical)
        values[canonical] = found
    return values, missing


def _build_caption(v):
    return (
        "\u2728 <b>DEPOSIT SUCCESSFULLY RECEIVED</b> \u2728\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\U0001F4B0 <b>Amount:</b> {v['amount']}\n\n"
        f"\U0001F464 <b>User Address:</b>\n<code>{v['address']}</code>\n\n"
        f"\U0001F517 <b>Transaction Hash:</b>\n<a href=\"https://bscscan.com/tx/{v['hash']}\">{v['hash']}</a>\n\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "\u2705 <b>Status:</b> Confirmed\n"
        "\U0001F510 <b>Transaction:</b> Verified on BNB Smart Chain\n\n"
        "Thank you for trusting AIDEFI!\n"
        "Your journey toward financial freedom starts here. \U0001F680"
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def _extract_from_where(payload):
    """Pull the source of the deposit. Accepts from_where / fromWhere / source."""
    for key in ("from_where", "fromWhere", "source"):
        val = payload.get(key)
        if val is not None and str(val).strip() != "":
            return str(val).strip().lower()
    return DEFAULT_FROM_WHERE


@app.route("/deposit", methods=["POST"])
def deposit():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}

    values, missing = _extract(payload)
    from_where = _extract_from_where(payload)
    if missing:
        return (
            jsonify({
                "ok": False,
                "error": "missing fields",
                "missing": missing,
                "expected": {k: aliases[0] for k, aliases in FIELD_ALIASES.items()},
            }),
            400,
        )

    try:
        image_bytes = fill_deposit_image(values["amount"], values["address"], values["hash"])
    except Exception as exc:  # image generation failure
        _record(values, from_where, status="error", error=f"image: {exc}")
        return jsonify({"ok": False, "error": f"image generation failed: {exc}"}), 500

    caption = _build_caption(values)

    try:
        result = send_photo(image_bytes, caption=caption)
    except TelegramError as exc:
        _record(values, from_where, status="telegram_error", error=str(exc))
        return jsonify({"ok": False, "error": str(exc)}), 502

    message_id = result.get("result", {}).get("message_id")
    deposit_id = _record(values, from_where, status="sent", telegram_message_id=message_id)

    return jsonify({
        "ok": True,
        "message": "deposit image sent to Telegram",
        "telegram_message_id": message_id,
        "deposit_id": deposit_id,
        "from_where": from_where,
    })


def _record(values, from_where, status, telegram_message_id=None, error=None):
    """Persist a deposit row; never let a DB error break the response."""
    try:
        return db.insert_deposit(
            amount=values.get("amount"),
            address=values.get("address"),
            tx_hash=values.get("hash"),
            from_where=from_where,
            status=status,
            telegram_message_id=telegram_message_id,
            error=error,
        )
    except Exception as exc:  # storage must not break the deposit flow
        app.logger.error("failed to store deposit: %s", exc)
        return None


@app.route("/deposits", methods=["GET"])
def list_deposits():
    """Read stored deposits. Optional query params: limit, offset, from_where, address."""
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"ok": False, "error": "limit/offset must be integers"}), 400

    from_where = request.args.get("from_where")
    address = request.args.get("address")

    rows = db.list_deposits(limit=limit, offset=offset, from_where=from_where, address=address)
    total = db.count_deposits(from_where=from_where, address=address)
    return jsonify({"ok": True, "total": total, "count": len(rows), "deposits": rows})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5005"))
    app.run(host="0.0.0.0", port=port)
