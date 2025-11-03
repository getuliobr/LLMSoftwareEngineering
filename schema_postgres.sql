CREATE TABLE IF NOT EXISTS users (
  id       SERIAL PRIMARY KEY,
  name     TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS labels (
  id       SERIAL PRIMARY KEY,
  name     TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS issues (
  id              INTEGER PRIMARY KEY,
  number          INTEGER,
  title           TEXT NOT NULL,
  state           TEXT,
  author_id       INTEGER,
  created_at      TIMESTAMP,
  updated_at      TIMESTAMP,
  closed_at       TIMESTAMP,
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

CREATE INDEX IF NOT EXISTS idx_issues_number ON issues(number);
CREATE INDEX IF NOT EXISTS idx_issues_state ON issues(state);
CREATE INDEX IF NOT EXISTS idx_issues_author ON issues(author_id);
CREATE INDEX IF NOT EXISTS idx_issue_assignees_user ON issue_assignees(user_id);
CREATE INDEX IF NOT EXISTS idx_issue_labels_label ON issue_labels(label_id);