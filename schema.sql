CREATE TYPE CampaignState AS ENUM ('awaiting', 'started');

CREATE TABLE IF NOT EXISTS Campaigns (
    guild_id   BIGINT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    state      CampaignState NOT NULL DEFAULT 'awaiting'
);

CREATE TABLE IF NOT EXISTS Giftees (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    guild_id    BIGINT NOT NULL REFERENCES Campaigns(guild_id) ON DELETE CASCADE,
    UNIQUE      (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS Memberships (
    user_id      BIGINT NOT NULL,
    guild_id     BIGINT NOT NULL REFERENCES Campaigns(guild_id) ON DELETE CASCADE,
    is_organizer BOOLEAN NOT NULL DEFAULT FALSE,
    giftee       INTEGER REFERENCES Giftees(id) DEFAULT NULL,
    PRIMARY KEY  (user_id, guild_id)
);