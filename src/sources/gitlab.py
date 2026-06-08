"""GitLab source — MRs, pipelines, mentions.

Uses python-gitlab SDK to fetch activity from GitLab instances.
"""

from __future__ import annotations

import logging

import gitlab

from src.config import GitLabInstanceConfig

from .base import ClassifiedItem, Source, SourceItem

log = logging.getLogger(__name__)


class GitLabSource(Source[GitLabInstanceConfig]):
    """GitLab activity source: open MRs, failed pipelines, mentions."""

    @property
    def source_name(self) -> str:
        return "gitlab"

    async def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        config = self.config

        try:
            gl = gitlab.Gitlab(
                config.url,
                private_token=config.token.get_secret_value(),
                ssl_verify=True,
            )
            gl.auth()
        except Exception as e:
            log.error("GitLab auth failed for %s: %s", config.name, e)
            return items

        user_id = gl.user.id

        for group_path in config.groups:
            try:
                group = gl.groups.get(group_path)
            except Exception:
                log.warning("Failed to get GitLab group %s", group_path)
                continue

            # Fetch open MRs awaiting review
            if config.watch_my_mrs:
                try:
                    mrs = group.mergerequests.list(
                        state="opened", get_all=False
                    )
                    for mr in mrs:
                        if mr.assignee and mr.assignee.get("id") == user_id:
                            items.append(
                                SourceItem(
                                    id=f"gitlab:{config.name}:mr:{mr.id}",
                                    source="gitlab",
                                    title=f"MR: {mr.title}",
                                    body=mr.description or "",
                                    url=mr.web_url,
                                    metadata={
                                        "type": "mr",
                                        "group": group_path,
                                        "author": mr.author.get("name", ""),
                                    },
                                )
                            )
                except Exception:
                    log.exception("Failed to fetch MRs for %s", group_path)

            # Fetch failed pipelines
            if config.watch_pipelines:
                try:
                    projects = group.projects.list(get_all=False)
                    for proj in projects:
                        try:
                            pipelines = gl.projects.get(
                                proj.id
                            ).pipelines.list(
                                status="failed", per_page=5, get_all=False
                            )
                            for pipe in pipelines:
                                items.append(
                                    SourceItem(
                                        id=f"gitlab:{config.name}:pipeline:{proj.id}:{pipe.id}",
                                        source="gitlab",
                                        title=f"Failed pipeline: {proj.name}",
                                        body=f"Pipeline {pipe.id} failed on {pipe.ref}",
                                        url=f"{config.url}/{proj.path_with_namespace}/-/pipelines/{pipe.id}",
                                        metadata={
                                            "type": "pipeline",
                                            "project": proj.name,
                                            "ref": pipe.ref,
                                        },
                                    )
                                )
                        except Exception:
                            continue
                except Exception:
                    log.exception("Failed to fetch pipelines for %s", group_path)

        return items

    async def classify(self, item: SourceItem) -> ClassifiedItem:
        priority = "high" if item.metadata.get("type") == "pipeline" else "medium"
        return ClassifiedItem(
            item=item,
            category="notification",
            action="read",
            priority=priority,
            summary=item.title,
            action_items=[f"{item.title} — {item.url}"] if item.url else [],
            requires_response=item.metadata.get("type") == "mr",
        )

    async def act(self, item: ClassifiedItem) -> None:
        pass  # GitLab source is read-only; no actions to execute
