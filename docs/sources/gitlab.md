# GitLab Source

Fetches activity from GitLab instances: open MRs, failed pipelines, and mentions.

## How It Works

1. Authenticates with the GitLab instance
2. For each configured group, fetches:
   - Open MRs assigned to the user
   - Failed pipelines in group projects
3. Classifies items by type (MR = medium, pipeline = high priority)
4. Stores action items in the database

## Configuration

```dotenv
WS_OPS_GITLAB_INSTANCES='[{
  "name": "myinstance",
  "url": "https://gitlab.com",
  "token": "glpat-...",
  "groups": ["my-group"],
  "watch_my_mrs": true,
  "watch_pipelines": true
}]'
```
