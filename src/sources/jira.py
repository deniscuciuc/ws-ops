"""Jira source — sprint, assigned issues.

Uses atlassian-python-api (jira lib) to fetch Jira activity.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from jira import JIRA
from jira.exceptions import JIRAError

from src.config import JiraInstanceConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)


class JiraSource(Source[JiraInstanceConfig]):
    """Jira activity source: assigned issues, sprint progress, recent updates."""

    @property
    def source_name(self) -> str:
        return "jira"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        try:
            jira = JIRA(
                server=config.server,
                basic_auth=(config.email, config.token.get_secret_value()),
            )
        except JIRAError as e:
            log.error("Jira auth failed for %s: %s", config.name, e)
            return items

        jql_parts: list[str] = []
        if config.projects:
            project_filter = ", ".join(f'"{p}"' for p in config.projects)
            jql_parts.append(f"project IN ({project_filter})")

        jql_parts.append("assignee = currentUser()")
        jql_parts.append("(status NOT IN (Done, Closed, Resolved) OR updated >= -7d)")
        jql = " AND ".join(jql_parts)

        try:
            issues = jira.search_issues(jql, maxResults=50)
        except JIRAError as e:
            log.error("Jira search failed for %s: %s", config.name, e)
            return items

        for issue in issues:
            fields = issue.fields
            priority = getattr(fields, "priority", None)
            priority_name = priority.name if priority else "Medium"
            status = getattr(fields, "status", None)
            status_name = status.name if status else "Unknown"
            due = getattr(fields, "duedate", None)

            ts = datetime.now(UTC)

            items.append(
                SourceItem(
                    id=f"jira:{config.name}:{issue.key}",
                    source="jira",
                    title=f"[{issue.key}] {fields.summary}",
                    body=f"Status: {status_name}\nPriority: {priority_name}\nDue: {due or 'None'}",
                    url=f"{config.server}/browse/{issue.key}",
                    timestamp=ts,
                    metadata={
                        "key": issue.key,
                        "status": status_name,
                        "priority": priority_name,
                        "due": due,
                    },
                )
            )

        return items

    async def classify(self, item: SourceItem) -> ClassifiedItem:
        priority = "high" if item.metadata.get("priority") in ("Highest", "High") else "medium"
        due = item.metadata.get("due")
        if due:
            priority = "high"

        return ClassifiedItem(
            item=item,
            category="work",
            action="read",
            priority=priority,
            summary=f"{item.metadata.get('key', '')}: {item.title}",
            action_items=[f"{item.title} — {item.url}"] if item.url else [],
            requires_response=False,
        )

    async def act(self, item: ClassifiedItem) -> None:
        pass  # Jira source is read-only
