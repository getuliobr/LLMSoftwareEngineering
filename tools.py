import json
import os
import psycopg2
import requests
from langchain_core.tools import tool
import sqlite3
from pathlib import Path
from ddgs import DDGS
import requests
from bs4 import BeautifulSoup
from logger import logger
from dotenv import load_dotenv
load_dotenv()

@tool
def github_search(query: str, sort: str = 'created', order: str = 'asc'):
    """Perform a GitHub issue search using the GitHub API and return the top 30 results in JSON format.

    Args:
        query (str): The search query that DOEST NOT include sorting arguments. Example of search: "repo:octocat/Hello-World is:issue is:open bug" to search for open issues labeled "bug" in the octocat/Hello-World repository.
        sort (str): The field to sort results by. Default is 'created'. Options include 'comments', 'created', 'updated'.
        order (str): The order of sorting. 'asc' for ascending, 'desc' for descending. Default is 'asc'.
    """
    logger.info(f"Searching GitHub for: {query}", extra={"role": "github_search", "tool_name": "github_search"})
    headers = {"Accept": "application/vnd.github.v3+json"}
    r = requests.get(f"https://api.github.com/search/issues?q={query}&sort={sort}&order={order}", headers=headers)
    if r.status_code == 200:
        return json.dumps(r.json().get("items", []), indent=2)
    return '{}'

@tool
def sql_query_executor(query: str):
    """Execute a SQL query against the GitHub issues database (sqlite) and return the results as JSON.
    Knowing that the database schema is as follows:
    ```sql
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS labels (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        name     TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS issues (
        id              INTEGER PRIMARY KEY,
        number          INTEGER,
        title           TEXT NOT NULL,
        state           TEXT,
        author_id       INTEGER,
        created_at      TEXT,
        updated_at      TEXT,
        closed_at       TEXT,
        comments_count  INTEGER,
        url             TEXT UNIQUE,
        FOREIGN KEY(author_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS issue_assignees (
        issue_id   INTEGER NOT NULL,
        user_id    INTEGER NOT NULL,
        PRIMARY KEY (issue_id, user_id),
        FOREIGN KEY(issue_id) REFERENCES issues(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id)  REFERENCES users(id)  ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS issue_labels (
        issue_id   INTEGER NOT NULL,
        label_id   INTEGER NOT NULL,
        PRIMARY KEY (issue_id, label_id),
        FOREIGN KEY(issue_id) REFERENCES issues(id) ON DELETE CASCADE,
        FOREIGN KEY(label_id) REFERENCES labels(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_issues_number   ON issues(number);
    CREATE INDEX IF NOT EXISTS idx_issues_state    ON issues(state);
    CREATE INDEX IF NOT EXISTS idx_issues_author   ON issues(author_id);
    CREATE INDEX IF NOT EXISTS idx_issue_assignees_user ON issue_assignees(user_id);
    CREATE INDEX IF NOT EXISTS idx_issue_labels_label   ON issue_labels(label_id);
    ```

    Args:
        query (str): The SQL query to execute.
    """
    logger.info(f"Executing SQL query: {query}", extra={"role": "sql_query_executor", "tool_name": "sql_query_executor"})
    database_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
    if database_type == 'postgresql':
        with psycopg2.connect(os.environ['DATABASE_URL'], options='-c default_transaction_read_only=on') as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                return json.dumps(results, indent=2)
    else:
        sqlite_file = Path('./issues.sqlite')
        with sqlite3.connect(sqlite_file) as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            return json.dumps(results, indent=2)

@tool
def get_user_info(name: str):
    """Get GitHub user information by username. Example:
    name: "octocat"
    ```json
    {
        "login": "octocat",
        "id": 583231,
        "node_id": "MDQ6VXNlcjU4MzIzMQ==",
        "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
        "gravatar_id": "",
        "url": "https://api.github.com/users/octocat",
        "html_url": "https://github.com/octocat",
        "followers_url": "https://api.github.com/users/octocat/followers",
        "following_url": "https://api.github.com/users/octocat/following{/other_user}",
        "gists_url": "https://api.github.com/users/octocat/gists{/gist_id}",
        "starred_url": "https://api.github.com/users/octocat/starred{/owner}{/repo}",
        "subscriptions_url": "https://api.github.com/users/octocat/subscriptions",
        "organizations_url": "https://api.github.com/users/octocat/orgs",
        "repos_url": "https://api.github.com/users/octocat/repos",
        "events_url": "https://api.github.com/users/octocat/events{/privacy}",
        "received_events_url": "https://api.github.com/users/octocat/received_events",
        "type": "User",
        "user_view_type": "public",
        "site_admin": false,
        "name": "The Octocat",
        "company": "@github",
        "blog": "https://github.blog",
        "location": "San Francisco",
        "email": null,
        "hireable": null,
        "bio": null,
        "twitter_username": null,
        "public_repos": 8,
        "public_gists": 8,
        "followers": 19891,
        "following": 9,
        "created_at": "2011-01-25T18:44:36Z",
        "updated_at": "2025-09-22T11:29:08Z"
    }
    ```

    Args:
        name (str): GitHub username.
    """
    logger.info(f"Fetching user info for: {name}", extra={"role": "get_user_info", "tool_name": "get_user_info"})
    r = requests.get(f"https://api.github.com/users/{name}")
    if r.status_code == 200:
        essencial_data = {
            "login": r.json().get("login"),
            "url": r.json().get("url"),
            "html_url": r.json().get("html_url"),
            "name": r.json().get("name"),
            "company": r.json().get("company"),
            "blog": r.json().get("blog"),
            "location": r.json().get("location"),
            "public_repos": r.json().get("public_repos"),
            "email": r.json().get("email"),
            "type": r.json().get("type")
        }
        return json.dumps(essencial_data, indent=2)
    return '{}'

@tool
def web_search(query: str):
    """Perform a web search using DuckDuckGo and return the top 10 results in JSON format.
    Args:
        query (str): The search query.
    """
    logger.info(f"Searching: {query}", extra={"role": "web_search", "tool_name": "web_search"})

    results = DDGS().text(query, max_results=10)
    return json.dumps(results, indent=2)

@tool
def get_repository_directory_structure(owner: str, repo: str):
    """Fetch the directory structure of a GitHub repository using the GitHub API.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
    """

    try:
        logger.info(f"Fetching repository: {owner}/{repo} directory structure", extra={"role": "get_repository_directory_structure", "tool_name": "get_repository_directory_structure"})
        r = requests.get(f"https://gitingest.com/api/ingest", json={
                "input_text":f"https://github.com/{owner}/{repo}",
                "token":"",
                "max_file_size":"46",
                "pattern_type":"exclude",
                "pattern":""
            }
        )
        return r.json().get('tree', 'No directory structure found')
    except Exception as e:
        return f"Error fetching repository structure: {e}"

@tool
def get_repository_issue_info(owner: str, repo: str, issue_number: int):
    """Fetch information about a specific issue in a GitHub repository. Example:
    owner: "octocat"
    repo: "Hello-World"
    issue_number: 42
    ```json
    {
        "url": "https://api.github.com/repos/octocat/Hello-World/issues/42",
        "repository_url": "https://api.github.com/repos/octocat/Hello-World",
        "labels_url": "https://api.github.com/repos/octocat/Hello-World/issues/42/labels{/name}",
        "comments_url": "https://api.github.com/repos/octocat/Hello-World/issues/42/comments",
        "events_url": "https://api.github.com/repos/octocat/Hello-World/issues/42/events",
        "html_url": "https://github.com/octocat/Hello-World/issues/42",
        "id": 5575402,
        "node_id": "MDU6SXNzdWU1NTc1NDAy",
        "number": 42,
        "title": "Found a bug",
        "user": {
            "login": "swathi-dhoddusamy1",
            "id": 1862021,
            "node_id": "MDQ6VXNlcjE4NjIwMjE=",
            "avatar_url": "https://avatars.githubusercontent.com/u/1862021?v=4",
            "gravatar_id": "",
            "url": "https://api.github.com/users/swathi-dhoddusamy1",
            "html_url": "https://github.com/swathi-dhoddusamy1",
            "followers_url": "https://api.github.com/users/swathi-dhoddusamy1/followers",
            "following_url": "https://api.github.com/users/swathi-dhoddusamy1/following{/other_user}",
            "gists_url": "https://api.github.com/users/swathi-dhoddusamy1/gists{/gist_id}",
            "starred_url": "https://api.github.com/users/swathi-dhoddusamy1/starred{/owner}{/repo}",
            "subscriptions_url": "https://api.github.com/users/swathi-dhoddusamy1/subscriptions",
            "organizations_url": "https://api.github.com/users/swathi-dhoddusamy1/orgs",
            "repos_url": "https://api.github.com/users/swathi-dhoddusamy1/repos",
            "events_url": "https://api.github.com/users/swathi-dhoddusamy1/events{/privacy}",
            "received_events_url": "https://api.github.com/users/swathi-dhoddusamy1/received_events",
            "type": "User",
            "user_view_type": "public",
            "site_admin": false
        },
        "labels": [

        ],
        "state": "open",
        "locked": false,
        "assignee": null,
        "assignees": [

        ],
        "milestone": null,
        "comments": 17,
        "created_at": "2012-07-12T16:03:48Z",
        "updated_at": "2025-04-11T20:24:23Z",
        "closed_at": null,
        "author_association": "NONE",
        "active_lock_reason": null,
        "sub_issues_summary": {
            "total": 0,
            "completed": 0,
            "percent_completed": 0
        },
        "issue_dependencies_summary": {
            "blocked_by": 0,
            "total_blocked_by": 0,
            "blocking": 0,
            "total_blocking": 0
        },
        "body": "I'm having a problem with this.\n",
        "closed_by": null,
        "reactions": {
            "url": "https://api.github.com/repos/octocat/Hello-World/issues/42/reactions",
            "total_count": 8,
            "+1": 4,
            "-1": 0,
            "laugh": 0,
            "hooray": 1,
            "confused": 0,
            "heart": 1,
            "rocket": 1,
            "eyes": 1
        },
        "timeline_url": "https://api.github.com/repos/octocat/Hello-World/issues/42/timeline",
        "performed_via_github_app": null,
        "state_reason": null
    }
    ```

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        issue_number (int): The issue number.
    """

    try:
        logger.info(f"Fetching {owner}/{repo} issue: {issue_number}", extra={"role": "get_repository_issue_info", "tool_name": "get_repository_issue_info"})
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}")
        if r.status_code == 200:
            essential_data = {
                "url": r.json().get("url"),
                "repository_url": r.json().get("repository_url"),
                "comments_url": r.json().get("comments_url"),
                "events_url": r.json().get("events_url"),
                "html_url": r.json().get("html_url"),
                "id": r.json().get("id"),
                "number": r.json().get("number"),
                "title": r.json().get("title"),
                "user": r.json().get("user")["login"] if r.json().get("user") else None,
                "labels": [label.get("name") for label in r.json().get("labels", [])],
                "state": r.json().get("state"),
                "assignees": [assignee.get("login") for assignee in r.json().get("assignees", [])],
                "comments": r.json().get("comments"),
                "created_at": r.json().get("created_at"),
                "updated_at": r.json().get("updated_at"),
                "closed_at": r.json().get("closed_at"),
                "body": r.json().get("body"),
                "closed_by": r.json().get("closed_by")["login"] if r.json().get("closed_by") else None,
                "timeline_url": r.json().get("timeline_url")
            }
            return json.dumps(essential_data, indent=2)
        return '{}'
    except Exception as e:
        return f"Error fetching repository info: {e}"

@tool
def visit_url(url: str):
    """Fetch the content of a URL.
    Args:
        url (str): The URL to visit.
    """
    try:
        logger.info(f"Visiting URL: {url}", extra={"role": "visit_url", "tool_name": "visit_url"})
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        return text[:2000]
    except Exception as e:
        return f"Error fetching URL {url}: {e}"