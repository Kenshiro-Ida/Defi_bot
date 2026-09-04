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

from image_filler import fill_deposit_image
from telegram_client import TelegramError, send_photo

app = Flask(__name__)

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


@app.route("/deposit", methods=["POST"])
def deposit():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}

    values, missing = _extract(payload)
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
        return jsonify({"ok": False, "error": f"image generation failed: {exc}"}), 500

    caption = _build_caption(values)

    try:
        result = send_photo(image_bytes, caption=caption)
    except TelegramError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502

    return jsonify({
        "ok": True,
        "message": "deposit image sent to Telegram",
        "telegram_message_id": result.get("result", {}).get("message_id"),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5005"))
    app.run(host="0.0.0.0", port=port)
