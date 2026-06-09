# Telegram Source

Reads messages from groups, channels, and DMs using Telethon (MTProto client).
Uses the user's own Telegram account — can read any chat the user can see.

## How It Works

1. Connects via Telethon using session file
2. Iterates dialogs and watches configured chats
3. Fetches unread messages (respecting limit)
4. Classifies with LLM to extract action items, decisions, and mentions
5. Stores extracted items in the database

## Authentication

Regular digest runs do not prompt for Telegram credentials. Authenticate once with:
```bash
ws-ops telegram-login personal
```

That one-time login uses the configured `session_file` path and stores the saved session there.

During the interactive login, Telethon asks for:
```
Enter your phone number: +1234567890
Enter the code: 12345
```

If you prefer env-only setup, provide `session_string` instead of `session_file`.

## Privacy

- DMs are opt-in (`fetch_dms: false` by default)
- Only configured chats are monitored
- Messages are processed by LLM (local Ollama keeps data private)

## Configuration

```dotenv
WS_OPS_TELEGRAM_ACCOUNTS='[{
  "name": "personal",
  "api_id": 12345678,
  "api_hash": "abc...",
  "session_file": null,
  "session_string": null,
  "watch_chats": ["team_chat", -1001234567890],
  "fetch_dms": false,
  "unread_only": true,
  "message_limit": 100
}]'
```
