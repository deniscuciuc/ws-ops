# Email Source

Fetches UNSEEN emails from IMAP INBOX, classifies each with LLM, and
auto-organizes into folders.

## How It Works

1. Connects to IMAP server and fetches unseen messages
2. Classifies each email using the `email_classify` prompt (category, priority, action, folder)
3. Executes the recommended action (move folder, mark read, delete)
4. Deduplicates by Message-ID against SQLite
5. Extracts action items into the database

## Actions

| Action | Behavior |
|--------|----------|
| `archive` | Move to configured archive folder |
| `delete` | Move to Trash |
| `read` | Mark as SEEN |
| `reply` | Flag for user (no auto-reply) |
| `forward` | Flag for user |

## Configuration

See `.env.example` — requires IMAP host, port, credentials, and folder mapping.
