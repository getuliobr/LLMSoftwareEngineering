PRAGMA foreign_keys = ON;

-- =========================================
-- Core entities
-- =========================================

CREATE TABLE user (
    id         INTEGER PRIMARY KEY,
    login      TEXT,
    followers  INTEGER,
    following  INTEGER,
    created_at TIMESTAMP
);

CREATE TABLE repository (
    id        INTEGER PRIMARY KEY,
    url       TEXT,
    license   TEXT,
    full_name TEXT,
    language  TEXT,
    forks     INTEGER,
    stars     INTEGER
);

CREATE TABLE issue (
    id         INTEGER PRIMARY KEY,
    number     INTEGER,
    title      TEXT,
    body       TEXT,
    user       TEXT,
    state      TEXT,
    created_at TIMESTAMP,
    closed_at  TIMESTAMP,
    html_url   TEXT
);

CREATE TABLE pull_request (
    id         INTEGER PRIMARY KEY,
    number     INTEGER,
    title      TEXT,
    body       TEXT,
    agent      TEXT,
    user_id    INTEGER,
    user       TEXT,
    state      TEXT,
    created_at TIMESTAMP,
    closed_at  TIMESTAMP,
    merged_at  TIMESTAMP,
    repo_id    INTEGER,
    repo_url   TEXT,
    html_url   TEXT,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (repo_id) REFERENCES repository(id)
);

-- =========================================
-- PR classification
-- =========================================

-- Uma linha por PR com a classificação de task type
CREATE TABLE pr_task_type (
    id         INTEGER PRIMARY KEY,             -- PR id
    agent      TEXT,
    title      TEXT,
    reason     TEXT,
    type       TEXT,
    confidence INTEGER,
    FOREIGN KEY (id) REFERENCES pull_request(id)
);

-- =========================================
-- Comments & reviews
-- =========================================

CREATE TABLE pr_comments (
    id         INTEGER PRIMARY KEY,
    pr_id      INTEGER,
    user       TEXT,
    user_id    INTEGER,
    user_type  TEXT,
    created_at TIMESTAMP,
    body       TEXT,
    FOREIGN KEY (pr_id)   REFERENCES pull_request(id),
    FOREIGN KEY (user_id) REFERENCES user(id)
);

CREATE TABLE pr_reviews (
    id           INTEGER PRIMARY KEY,
    pr_id        INTEGER,
    user         TEXT,
    user_type    TEXT,
    state        TEXT,
    submitted_at TIMESTAMP,
    body         TEXT,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

CREATE TABLE pr_review_comments (
    id                     INTEGER PRIMARY KEY,
    pull_request_review_id INTEGER,
    user                   TEXT,
    user_type              TEXT,
    diff_hunk              TEXT,
    path                   TEXT,
    position               INTEGER,
    original_position      INTEGER,
    commit_id              TEXT,
    original_commit_id     TEXT,
    body                   TEXT,
    pull_request_url       TEXT,
    created_at             TIMESTAMP,
    updated_at             TIMESTAMP,
    in_reply_to_id         INTEGER,
    FOREIGN KEY (pull_request_review_id) REFERENCES pr_reviews(id),
    FOREIGN KEY (in_reply_to_id)         REFERENCES pr_review_comments(id)
);

-- =========================================
-- Commits & file-level details
-- =========================================

CREATE TABLE pr_commits (
    id  INTEGER PRIMARY KEY AUTOINCREMENT, 
    sha       TEXT,
    pr_id     INTEGER,
    author    TEXT,
    committer TEXT,
    message   TEXT,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

CREATE TABLE pr_commit_details (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    sha                    TEXT,
    pr_id                  INTEGER,
    author                 TEXT,
    committer              TEXT,
    message                TEXT,
    commit_stats_total     INTEGER,
    commit_stats_additions INTEGER,
    commit_stats_deletions INTEGER,
    filename               TEXT,
    status                 TEXT,
    additions              INTEGER,
    deletions              INTEGER,
    changes                INTEGER,
    patch                  TEXT,
    FOREIGN KEY (sha, pr_id) REFERENCES pr_commits(sha, pr_id)
);

-- =========================================
-- Timeline & issue relations
-- =========================================

CREATE TABLE pr_timeline (
    pr_id      INTEGER,
    event      TEXT,
    commit_id  TEXT,
    created_at TIMESTAMP,
    actor      TEXT,
    assignee   TEXT,
    label      TEXT,
    message    TEXT,
    FOREIGN KEY (pr_id) REFERENCES pull_request(id)
);

CREATE TABLE related_issue (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_id    INTEGER,
    issue_id INTEGER,
    source   TEXT,
    FOREIGN KEY (pr_id)    REFERENCES pull_request(id),
    FOREIGN KEY (issue_id) REFERENCES issue(id)
);
