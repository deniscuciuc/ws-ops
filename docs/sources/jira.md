# Jira Source

Fetches assigned issues, sprint progress, and recent updates from Jira instances.

## How It Works

1. Authenticates with Jira using basic auth (email + API token)
2. Searches for issues assigned to the current user across configured projects
3. Includes non-Done issues and recently updated items
4. Classifies by priority and due date
5. Stores action items in the database

## Configuration

```dotenv
WS_OPS_JIRA_INSTANCES='[{
  "name": "myorg",
  "server": "https://myorg.atlassian.net",
  "email": "user@example.com",
  "token": "jira-api-token",
  "projects": ["PROJ", "OTH"]
}]'
```

Generate an API token at: https://id.atlassian.com/manage/api-tokens
