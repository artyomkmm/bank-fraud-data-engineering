CREATE TABLE IF NOT EXISTS app_sessions (
    session_id VARCHAR(40) PRIMARY KEY,
    customer_id INT NOT NULL,
    login_time TIMESTAMP,
    logout_time TIMESTAMP,
    device_type VARCHAR(20),
    app_version VARCHAR(20),
    ip_address VARCHAR(40),
    os_version VARCHAR(30),
    is_new_device BOOLEAN
);

CREATE TABLE IF NOT EXISTS app_events (
    event_id BIGINT PRIMARY KEY,
    session_id VARCHAR(40) NOT NULL,
    customer_id INT NOT NULL,
    event_time TIMESTAMP,
    event_type VARCHAR(50),
    event_data JSONB,
    is_successful BOOLEAN,
    error_message VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_app_sessions_customer_id ON app_sessions(customer_id);
CREATE INDEX IF NOT EXISTS idx_app_events_session_id ON app_events(session_id);
CREATE INDEX IF NOT EXISTS idx_app_events_customer_id ON app_events(customer_id);
