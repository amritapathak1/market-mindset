-- PostgreSQL Schema for Stock Market Mindset
-- Optimized for AWS RDS Free Tier (db.t2.micro)

-- Drop all tables (use CASCADE to handle foreign key dependencies)
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS page_visits CASCADE;
DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS confidence_risk CASCADE;
DROP TABLE IF EXISTS portfolio CASCADE;
DROP TABLE IF EXISTS task_responses CASCADE;
DROP TABLE IF EXISTS demographics CASCADE;
DROP TABLE IF EXISTS participants CASCADE;

-- Participants table
CREATE TABLE IF NOT EXISTS participants (
    participant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),  -- Nullable for anonymous participants
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    withdrawn BOOLEAN DEFAULT FALSE,
    withdrawn_at TIMESTAMP
);

-- Demographics data
CREATE TABLE IF NOT EXISTS demographics (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    age_range VARCHAR(20),
    gender VARCHAR(50),
    gender_self_describe VARCHAR(100),
    education VARCHAR(100),
    income VARCHAR(50),
    experience VARCHAR(100),
    hispanic_latino VARCHAR(10),
    race VARCHAR(100),
    race_other VARCHAR(100),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(participant_id)
);

-- Task responses
CREATE TABLE IF NOT EXISTS task_responses (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL,
    stock_1_ticker VARCHAR(10),
    stock_1_name VARCHAR(255),
    stock_1_investment DECIMAL(10, 2),
    stock_2_ticker VARCHAR(10),
    stock_2_name VARCHAR(255),
    stock_2_investment DECIMAL(10, 2),
    total_investment DECIMAL(10, 2),
    remaining_amount DECIMAL(10, 2),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    time_spent_seconds INTEGER
);

-- Portfolio tracking (investments with returns)
CREATE TABLE IF NOT EXISTS portfolio (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL,
    stock_name VARCHAR(255),
    ticker VARCHAR(10),
    invested_amount DECIMAL(10, 2),
    return_percent DECIMAL(10, 4),
    final_value DECIMAL(10, 2),
    profit_loss DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Confidence and risk ratings
CREATE TABLE IF NOT EXISTS confidence_risk (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    confidence_rating INTEGER,
    risk_rating INTEGER,
    attention_check_response INTEGER,
    completed_after_task INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    feedback_text TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(participant_id)
);

-- Page visits (time tracking)
CREATE TABLE IF NOT EXISTS page_visits (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    page_name VARCHAR(100) NOT NULL,
    task_id INTEGER,
    entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    exited_at TIMESTAMP,
    duration_seconds INTEGER
);

-- Events table (comprehensive user interaction tracking)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    participant_id UUID REFERENCES participants(participant_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,  -- 'navigation', 'interaction', 'input', 'error', etc.
    page_name VARCHAR(100),
    task_id INTEGER,
    element_id VARCHAR(255),
    element_type VARCHAR(50),  -- 'button', 'modal', 'input', 'slider', etc.
    action VARCHAR(100),  -- 'click', 'open', 'close', 'change', 'focus', 'blur', etc.
    old_value TEXT,
    new_value TEXT,
    stock_ticker VARCHAR(10),
    metadata JSONB,  -- Additional flexible data
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_participants_session ON participants(session_id);
CREATE INDEX idx_participants_created ON participants(created_at);
CREATE INDEX idx_events_participant ON events(participant_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_category ON events(event_category);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_page ON events(page_name);
CREATE INDEX idx_page_visits_participant ON page_visits(participant_id);
CREATE INDEX idx_task_responses_participant ON task_responses(participant_id);
CREATE INDEX idx_portfolio_participant ON portfolio(participant_id);

-- View for participant summary
CREATE OR REPLACE VIEW participant_summary AS
SELECT 
    p.participant_id,
    p.session_id,
    p.created_at,
    p.completed,
    p.completed_at,
    d.age,
    d.gender,
    d.education,
    d.experience,
    COUNT(DISTINCT tr.task_id) as tasks_completed,
    SUM(tr.total_investment) as total_invested,
    cr.confidence_rating,
    cr.risk_rating,
    (SELECT COUNT(*) FROM events WHERE participant_id = p.participant_id) as total_events,
    (SELECT SUM(duration_seconds) FROM page_visits WHERE participant_id = p.participant_id) as total_time_seconds
FROM participants p
LEFT JOIN demographics d ON p.participant_id = d.participant_id
LEFT JOIN task_responses tr ON p.participant_id = tr.participant_id
LEFT JOIN confidence_risk cr ON p.participant_id = cr.participant_id
GROUP BY p.participant_id, p.session_id, p.created_at, p.completed, p.completed_at,
         d.age, d.gender, d.education, d.experience, cr.confidence_rating, cr.risk_rating;

-- Function to update last_active timestamp
CREATE OR REPLACE FUNCTION update_last_active()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE participants 
    SET last_active = CURRENT_TIMESTAMP 
    WHERE participant_id = NEW.participant_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update last_active on any event
CREATE TRIGGER update_participant_last_active
AFTER INSERT ON events
FOR EACH ROW
EXECUTE FUNCTION update_last_active();
