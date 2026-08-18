CREATE TABLE chatbots (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    system_prompt TEXT,
    temperature FLOAT NOT NULL DEFAULT 0.7,
    welcome_message TEXT,
    primary_color VARCHAR(50),
    avatar_url VARCHAR(500),
    embed_token VARCHAR(255) UNIQUE,
    status VARCHAR(50) NOT NULL,
    business_id BIGINT REFERENCES businesses(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chatbot_allowed_domains (
    id BIGSERIAL PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    chatbot_id BIGINT REFERENCES chatbots(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
