# Zengine Disbursement Monitor

Monitors Zengine form `185672` and sends a Telegram message for each approved disbursement allocation that has not been notified before.

Message format:

```text
New Disbursement Allocation added: $[amount] - [Disbursement Description for Payment Memo] - [Linked Payee]
```

## GitHub Actions Setup

This repo includes a scheduled GitHub Actions workflow at `.github/workflows/monitor-disbursements.yml`.

The workflow runs every 10 minutes Monday-Friday from 8:00 AM through 6:00 PM Eastern. This is cheaper than keeping a Render web service and database online, and it stays within GitHub's free Actions allowance more comfortably than an all-day schedule.

Add these repository secrets in GitHub:

- `ZENGINE_API_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

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

## State

The workflow stores already-notified Zengine record IDs in:

```text
state/notified_records.json
```

On the first successful run, existing approved records are marked as already seen and no backlog Telegram messages are sent.

Use GitHub's **Actions > Monitor approved disbursements > Run workflow** button to trigger a manual check.
