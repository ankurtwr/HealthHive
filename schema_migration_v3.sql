USE medcompare;

-- ── New table for storing analyzed medical reports ──────────────────────
CREATE TABLE IF NOT EXISTS user_reports (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    file_path       VARCHAR(500) NULL,
    report_type     VARCHAR(100) DEFAULT 'blood_test',
    raw_text        TEXT NULL,
    analysis_json   JSON NULL,
    diet_suggestions TEXT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Guest sessions (temporary, auto-purged) ────────────────────────────
CREATE TABLE IF NOT EXISTS guest_sessions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(128) NOT NULL UNIQUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL,
    INDEX idx_session (session_id),
    INDEX idx_expires (expires_at)
);

-- ── Guest reports (linked to session, cascade-deleted) ─────────────────
CREATE TABLE IF NOT EXISTS guest_reports (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(128) NOT NULL,
    file_path       VARCHAR(500) NULL,
    analysis_json   JSON NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES guest_sessions(session_id) ON DELETE CASCADE
);

-- ── Add is_guest flag to users table ───────────────────────────────────
ALTER TABLE users ADD COLUMN is_guest TINYINT(1) DEFAULT 0;
