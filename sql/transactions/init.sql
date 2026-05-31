CREATE TABLE IF NOT EXISTS transactions (
    trx_id BIGINT PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL,
    customer_id INT NOT NULL,
    card_id BIGINT,
    trx_datetime TIMESTAMP,
    trx_type VARCHAR(10),
    amount DECIMAL(18,2),
    currency CHAR(3),
    channel VARCHAR(30),
    merchant_category_code VARCHAR(4),
    counterparty_name VARCHAR(100),
    status VARCHAR(20),
    posting_date DATE
);

CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_datetime ON transactions(trx_datetime);
