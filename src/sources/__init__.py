"""Source modules for ws-ops."""

from __future__ import annotations

from src.registry import register_source
from src.sources.email import EmailSource
from src.sources.github import GitHubSource
from src.sources.gitlab import GitLabSource
from src.sources.jira import JiraSource
from src.sources.telegram import TelegramSource

register_source("email", "email_accounts", EmailSource)
register_source("gitlab", "gitlab_instances", GitLabSource)
register_source("github", "github_accounts", GitHubSource)
register_source("telegram", "telegram_accounts", TelegramSource)
register_source("jira", "jira_instances", JiraSource)

