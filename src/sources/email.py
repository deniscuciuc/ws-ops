"""Email source — IMAP fetch, LLM classify, folder actions.

Fetches UNSEEN emails from INBOX, classifies each with LLM,
and acts immediately (move folder, mark seen, flag for deletion).
Deduplicates against SQLite by Message-ID header.
"""

from __future__ import annotations

import contextlib
import imaplib
import logging
from datetime import UTC, datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

import imapclient

from src.config import EmailAccountConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)

ACTION_MAP = {
    "archive": lambda server, uid, folders: server.move([uid], folders.get("archive", "Archive")),
    "delete": lambda server, uid, _folders: server.move([uid], "Trash"),
    "read": lambda server, uid, _folders: server.add_flags([uid], [imapclient.SEEN]),
    "reply": lambda _server, _uid, _folders: None,
    "forward": lambda _server, _uid, _folders: None,
}


def decode_header_value(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    decoded_parts = decode_header(value)
    parts: list[str] = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                parts.append(part.decode("utf-8", errors="replace"))
        else:
            parts.append(str(part))
    return " ".join(parts)


def parse_email_date(date_str: str | None) -> datetime:
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            if dt and not dt.tzinfo:
                dt = dt.replace(tzinfo=UTC)
            if dt:
                return dt
        except Exception:
            pass
    return datetime.now(UTC)


class EmailSource(Source[EmailAccountConfig]):
    """IMAP email source with LLM-powered classification and auto-organization."""

    @property
    def source_name(self) -> str:
        return "email"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        try:
            server = imapclient.IMAPClient(
                config.host, port=config.port, ssl=config.use_ssl
            )
            server.login(config.username, config.password.get_secret_value())
        except (imaplib.IMAP4.error, OSError) as e:
            log.error("IMAP connection failed for %s: %s", config.name, e)
            return items

        try:
            server.select_folder("INBOX")
            messages = server.search("UNSEEN")
            if not messages:
                return items

            fetch_limit = config.fetch_limit
            if len(messages) > fetch_limit:
                messages = messages[:fetch_limit]

            raw = server.fetch(messages, ["FLAGS", "INTERNALDATE", "BODY[]"])

            for uid in messages:
                try:
                    data = raw[uid]
                    body_bytes = data.get(b"BODY[]", b"")
                    if not body_bytes:
                        continue

                    from email import message_from_bytes
                    msg = message_from_bytes(body_bytes)

                    msg_id = msg.get("Message-ID", "").strip()
                    if not msg_id:
                        msg_id = f"email:{config.name}:{uid}"

                    subject = decode_header_value(msg.get("Subject", ""))
                    sender = decode_header_value(msg.get("From", ""))
                    date_str = msg.get("Date")
                    date = parse_email_date(date_str)

                    body = _extract_text_body(msg)

                    items.append(
                        SourceItem(
                            id=f"email:{config.name}:{msg_id}",
                            source="email",
                            title=subject or "(no subject)",
                            body=body,
                            timestamp=date,
                            metadata={
                                "uid": uid,
                                "sender": sender,
                            },
                        )
                    )
                except Exception:
                    log.exception("Failed to process email UID %s", uid)

        finally:
            with contextlib.suppress(Exception):
                server.logout()

        return items

    async def classify(self, item: SourceItem) -> ClassifiedItem:
        assert self.prompt_manager is not None, "PromptManager required for classify"
        pm = self.prompt_manager
        folders_str = ", ".join(
            self.config.folders_map.values()
        ) or "inbox, archive, trash"

        user_msg = pm.render_user(
            "email_classify",
            folders=folders_str,
            sender=item.metadata.get("sender", ""),
            subject=item.title,
            date=item.timestamp.isoformat(),
            body=item.body[:800],
        )

        system_prompt = pm.get("email_classify").system
        response = await self.llm.complete(
            system=system_prompt, user=user_msg, expect_json=True
        )

        if response.parsed:
            data = response.parsed
        else:
            data = {
                "category": "notification",
                "action": "read",
                "priority": "low",
                "read_status": "read_later",
                "folder": "archive",
                "summary": item.title,
                "action_items": [],
                "requires_response": False,
            }

        return ClassifiedItem(
            item=item,
            category=data.get("category", "notification"),
            action=data.get("action", "read"),
            priority=data.get("priority", "low"),
            summary=data.get("summary", item.title),
            action_items=data.get("action_items", []),
            folder=data.get("folder"),
            requires_response=data.get("requires_response", False),
        )

    async def act(self, item: ClassifiedItem) -> None:
        action = item.action
        handler = ACTION_MAP.get(action)
        if handler is None:
            return

        config = self.config
        uid = item.item.metadata.get("uid")
        if uid is None:
            return

        if self.dry_run:
            log.info(
                "[DRY RUN] Would apply '%s' on UID %s → folder %s",
                action,
                uid,
                item.folder or "none",
            )
            return

        try:
            server = imapclient.IMAPClient(
                config.host, port=config.port, ssl=config.use_ssl
            )
            server.login(config.username, config.password.get_secret_value())
            server.select_folder("INBOX")
            handler(server, uid, config.folders_map)
            server.logout()
        except Exception:
            log.exception("Failed to execute action '%s' on UID %s", action, uid)


def _extract_text_body(msg: object) -> str:
    """Extract text content from an email message."""
    import email

    bodies: list[str] = []

    if isinstance(msg, email.message.Message):
        if msg.get_content_type() == "text/plain":
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                bodies.append(payload.decode("utf-8", errors="replace"))
        elif msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        bodies.append(payload.decode("utf-8", errors="replace"))

    return "\n".join(bodies)
