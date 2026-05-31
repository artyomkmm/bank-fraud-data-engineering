CREATE TABLE IF NOT EXISTS cards (
    card_id BIGINT PRIMARY KEY,
    account_id VARCHAR(20) NOT NULL,
    card_pan_hash VARCHAR(255),
    card_product VARCHAR(30),
    expiry_date DATE,
    embossed_name VARCHAR(100),
    card_status VARCHAR(20),
    issue_date DATE
);

CREATE INDEX IF NOT EXISTS idx_cards_account_id ON cards(account_id);
CREATE INDEX IF NOT EXISTS idx_cards_status ON cards(card_status);
