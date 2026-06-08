"""GitHub source — PRs, issues, CI.

Uses PyGitHub SDK to fetch activity from GitHub accounts.
"""

from __future__ import annotations

import contextlib
import logging

from github import Github
from github.GithubException import GithubException

from src.config import GitHubAccountConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)


class GitHubSource(Source[GitHubAccountConfig]):
    """GitHub activity source: open PRs, failed CI, mentions."""

    @property
    def source_name(self) -> str:
        return "github"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        try:
            gh = Github(config.token.get_secret_value())
            user = gh.get_user()
        except GithubException as e:
            log.error("GitHub auth failed for %s: %s", config.name, e)
            return items

        repos_to_check: list = []

        # Orgs configured
        for org_name in config.orgs:
            try:
                org = gh.get_organization(org_name)
                repos_to_check.extend(org.get_repos(type="member"))
            except GithubException:
                log.warning("Failed to get GitHub org %s", org_name)

        # Personal repos with recent activity
        with contextlib.suppress(GithubException):
            repos_to_check.extend(user.get_repos(sort="updated", per_page=10))

        seen = set()
        for repo in repos_to_check:
            if repo.full_name in seen:
                continue
            seen.add(repo.full_name)

            try:
                # PRs awaiting review
                if config.watch_my_prs:
                    prs = repo.get_pulls(state="open")
                    for pr in prs:
                        if pr.user.login != user.login:
                            continue  # only PRs by the user

                        requested = pr.get_review_requests()
                        if requested[0]:
                            items.append(
                                SourceItem(
                                    id=f"github:{config.name}:pr:{pr.id}",
                                    source="github",
                                    title=f"PR: {pr.title}",
                                    body=pr.body or "",
                                    url=pr.html_url,
                                    metadata={
                                        "type": "pr",
                                        "repo": repo.full_name,
                                        "reviews_waiting": len(requested[0]),
                                    },
                                )
                            )

                # Failed CI
                commits = repo.get_commits(sha=repo.default_branch, per_page=5)
                for commit in commits:
                    try:
                        status = commit.get_combined_status()
                        if status.state == "failure":
                            items.append(
                                SourceItem(
                                    id=f"github:{config.name}:ci:{commit.sha}",
                                    source="github",
                                    title=f"CI failure: {repo.name}",
                                    body=f"Commit {commit.sha[:8]} on {repo.default_branch}",
                                    url=f"{repo.html_url}/commits/{commit.sha}",
                                    metadata={
                                        "type": "ci",
                                        "repo": repo.full_name,
                                        "branch": repo.default_branch,
                                    },
                                )
                            )
                    except GithubException:
                        continue

            except GithubException:
                continue

        return items

    async def classify(self, item: SourceItem) -> ClassifiedItem:
        priority = "high" if item.metadata.get("type") == "ci" else "medium"
        return ClassifiedItem(
            item=item,
            category="notification",
            action="read",
            priority=priority,
            summary=item.title,
            action_items=[f"{item.title} — {item.url}"] if item.url else [],
            requires_response=item.metadata.get("type") == "pr",
        )

    async def act(self, item: ClassifiedItem) -> None:
        pass  # GitHub source is read-only
