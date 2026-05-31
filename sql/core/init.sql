CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(20) PRIMARY KEY,
    customer_id INT NOT NULL,
    product_type VARCHAR(30),
    currency CHAR(3),
    balance DECIMAL(18,2),
    opened_date DATE,
    closed_date DATE,
    status VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer_id ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
