# Zengine Disbursement Monitor

Monitors Zengine form `185672` and sends a Telegram message for each approved disbursement allocation that has not been notified before.

Message format:

```text
New Disbursement Allocation added: $[amount] - [Disbursement Description for Payment Memo] - [Linked Payee]
```

## GitHub Actions Setup

This repo includes two GitHub Actions workflows:

- `.github/workflows/monitor-disbursements.yml` for manual test runs.
- `.github/workflows/scheduled-monitor-disbursements.yml` for automatic scheduled runs.

The scheduled workflow runs during Eastern business hours on weekdays. Because GitHub cron uses UTC, the workflow uses separate UTC cron entries that map to 8:00 AM through 6:00 PM Eastern during daylight time, with an in-workflow Eastern-time guard as a backup.

Add these repository secrets in GitHub:

- `ZENGINE_LOGIN_EMAIL`
- `ZENGINE_LOGIN_PASSWORD`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Do not add `ZENGINE_API_TOKEN` for the normal GitHub Actions setup. Each scheduled run logs into the Zengine developer page, retrieves the current API token, masks it in the Actions log, uses it for that run, and discards it. `ZENGINE_API_TOKEN` is still supported only as an optional local/debug fallback.

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

Paste a Zengine token when prompted. The script prints likely Status, Memo/Description, Amount, and Payee fields.

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

Manual workflow runs send a Telegram status message when no new approved disbursements are found. Scheduled runs stay quiet unless a new approved record appears.
