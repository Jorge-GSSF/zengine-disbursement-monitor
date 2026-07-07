# Zengine Disbursement Monitor

Monitors Zengine form `185672` every 10 minutes and sends a Telegram message for each approved disbursement allocation that has not been notified before.

Message format:

```text
New Disbursement Allocation added: $[amount] - [Disbursement Description for Payment Memo] - [Linked Payee]
```

## Required Environment Variables

- `ZENGINE_API_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `DATABASE_URL`

Known field IDs from the existing automation:

- `ZENGINE_FORM_ID=185672`
- `ZENGINE_AMOUNT_FIELD_ID=field3583325`
- `ZENGINE_LINKED_PAYEE_FIELD_ID=field3588097`
- `ZENGINE_STATUS_FIELD_ID=field3589680`
- `ZENGINE_PAYMENT_MEMO_FIELD_ID=field6995603`

## Find The Missing Zengine Field IDs

Run:

```powershell
python tools/inspect_zengine_fields.py
```

Paste the Zengine token when prompted. The script prints likely Status, Memo/Description, Amount, and Payee fields.

## Find The Telegram Chat ID

1. Open the bot in Telegram.
2. Send `/start`.
3. Run:

```powershell
python tools/get_telegram_chat_id.py
```

Paste the Telegram bot token when prompted. Use the printed numeric `chat_id` as `TELEGRAM_CHAT_ID`.

## First Run Behavior

`NOTIFY_EXISTING_ON_FIRST_RUN=false` is intentional. On the first successful run, existing approved records are marked as already seen so the bot does not send a large backlog. Future approved records that are not in the database will send a Telegram alert.

Set `NOTIFY_EXISTING_ON_FIRST_RUN=true` only if you want the initial run to text every current approved record.

## Render

The included `render.yaml` provisions:

- one Python web service
- one Render Postgres database
- environment variable placeholders for secrets

Deploy from GitHub as a Render Blueprint, then fill the secret env vars in Render.

The manual `POST /run-once?secret=...` endpoint is protected by `RUN_ONCE_SECRET`; Render can generate this value automatically.
