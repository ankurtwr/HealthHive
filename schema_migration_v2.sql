USE medcompare;

-- Update users table to store terms acceptance status if columns don't exist
ALTER TABLE users 
  ADD COLUMN accepted_terms TINYINT(1) DEFAULT 0,
  ADD COLUMN accepted_terms_at DATETIME NULL;

-- Create table for user prescriptions
CREATE TABLE IF NOT EXISTS user_prescriptions (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    file_path      VARCHAR(500) NULL,
    extracted_text TEXT NULL,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create table for saved medicines
CREATE TABLE IF NOT EXISTS user_medicines (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    medicine_id INT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    UNIQUE KEY uq_user_med (user_id, medicine_id)
);

-- Create table for medicine reminders
CREATE TABLE IF NOT EXISTS medicine_reminders (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NOT NULL,
    medicine_name     VARCHAR(300) NOT NULL,
    dosage            VARCHAR(100) NULL,
    schedule_morning  TINYINT(1) DEFAULT 0,
    schedule_noon     TINYINT(1) DEFAULT 0,
    schedule_evening  TINYINT(1) DEFAULT 0,
    schedule_night    TINYINT(1) DEFAULT 0,
    instructions      VARCHAR(500) NULL,
    is_active         TINYINT(1) DEFAULT 1,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
