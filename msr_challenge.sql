PRAGMA foreign_keys = ON;

-- Users
CREATE TABLE user (
    id         INTEGER PRIMARY KEY,
    login      VARCHAR,
    followers  INTEGER,
    following  INTEGER,
    created_at TIMESTAMP
);

-- Repositories
CREATE TABLE repository (
    id        INTEGER PRIMARY KEY,
    url       VARCHAR,
    license   VARCHAR,
    full_name VARCHAR,
    language  VARCHAR,
    forks     INTEGER,
    stars     INTEGER
);

-- Issues
CREATE TABLE issue (
    id         INTEGER PRIMARY KEY,
    number     INTEGER,
    title      VARCHAR,
    body       TEXT,
    user       VARCHAR,
    state      VARCHAR,
    created_at TIMESTAMP,
    closed_at  TIMESTAMP,
    html_url   VARCHAR
);

-- Pull requests
CREATE TABLE pull_request (
    id         INTEGER PRIMARY KEY,
    number     INTEGER,
    title      VARCHAR,
    body       TEXT,
    agent      VARCHAR,
    user_id    INTEGER,
    user       VARCHAR,
    state      VARCHAR,
    created_at TIMESTAMP,
    closed_at  TIMESTAMP,
    merged_at  TIMESTAMP,
    repo_id    INTEGER,
    repo_url   VARCHAR,
    html_url   VARCHAR,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (repo_id) REFERENCES repository(id)
);

-- PR commits (one row per commit in a PR)
CREATE TABLE pr_commits (
    sha       VARCHAR,
    pr_id     INTEGER,
    author    VARCHAR,
    committer VARCHAR,
    message   TEXT,
    PRIMARY KEY (sha, pr_id),
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

-- Detailed commit info (per-file stats within a commit)
CREATE TABLE pr_commit_details (
    sha                    VARCHAR,
    pr_id                  INTEGER,
    author                 VARCHAR,
    committer              VARCHAR,
    message                TEXT,
    commit_stats_total     INTEGER,
    commit_stats_additions INTEGER,
    commit_stats_deletions INTEGER,
    filename               VARCHAR,
    status                 VARCHAR,
    additions              INTEGER,
    deletions              INTEGER,
    changes                INTEGER,
    patch                  TEXT,
    PRIMARY KEY (sha, pr_id, filename),
    FOREIGN KEY (sha, pr_id) REFERENCES pr_commits(sha, pr_id)
);

-- PR timeline events
CREATE TABLE pr_timeline (
    pr_id      INTEGER,
    event      VARCHAR,
    commit_id  VARCHAR,
    created_at TIMESTAMP,
    actor      VARCHAR,
    assignee   VARCHAR,
    label      VARCHAR,
    message    TEXT,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

-- Relation between PRs and issues
CREATE TABLE related_issue (
    pr_id    INTEGER,
    issue_id INTEGER,
    source   VARCHAR,
    FOREIGN KEY (pr_id)    REFERENCES pull_request(id),
    FOREIGN KEY (issue_id) REFERENCES issue(id)
);

-- PR comments (issue-style comments on the PR)
CREATE TABLE pr_comments (
    id         INTEGER PRIMARY KEY,
    pr_id      INTEGER,
    user       VARCHAR,
    user_id    INTEGER,
    created_at TIMESTAMP,
    body       TEXT,
    FOREIGN KEY (pr_id)   REFERENCES pull_request(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- PR task type (labels like "bugfix", "feature", etc.)
CREATE TABLE pr_task_type (
    pr_id INTEGER,
    type  VARCHAR,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

-- PR reviews (review objects)
CREATE TABLE pr_reviews (
    id           INTEGER PRIMARY KEY,
    pr_id        INTEGER,
    user         VARCHAR,
    state        VARCHAR,
    submitted_at TIMESTAMP,
    body         TEXT,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

-- PR review comments (inline review comments)
CREATE TABLE pr_review_comments (
    pull_request_review_id INTEGER,
    id                     INTEGER PRIMARY KEY,
    user                   VARCHAR,
    diff_hunk              TEXT,
    path                   VARCHAR,
    position               INTEGER,
    original_position      INTEGER,
    commit_id              VARCHAR,
    original_commit_id     VARCHAR,
    body                   TEXT,
    pull_request_url       VARCHAR,
    created_at             TIMESTAMP,
    updated_at             TIMESTAMP,
    in_reply_to_id         INTEGER,
    FOREIGN KEY (pull_request_review_id) REFERENCES pr_reviews(id),
    FOREIGN KEY (in_reply_to_id)         REFERENCES pr_review_comments(id)
);
