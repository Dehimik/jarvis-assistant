CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) логи
CREATE TABLE IF NOT EXISTS app_log (
  id         BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  level      TEXT NOT NULL,        -- DEBUG/INFO/WARNING/ERROR
  logger     TEXT,                 -- ім'я логера
  message    TEXT NOT NULL,
  context    JSONB,                -- довільні extra дані
  trace      TEXT                  -- traceback якщо є
);
CREATE INDEX IF NOT EXISTS idx_app_log_created_at ON app_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_log_level ON app_log(level);

-- 2) історія команд
CREATE TABLE IF NOT EXISTS command_history (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_text     TEXT,               -- що сказав/написав користувач
  intent       TEXT,               -- парсинг/канонічна інтенція
  slots        JSONB,              -- {"app":"telegram"}
  confidence   REAL,               -- 0..1
  session_id   UUID,               -- опціонально
  user_id      UUID,               -- опціонально
  status       TEXT NOT NULL DEFAULT 'parsed',  -- parsed|running|success|error
  error        TEXT,               -- якщо була помилка
  meta         JSONB               -- додаткові поля (stt model, latency, etc)
);
CREATE INDEX IF NOT EXISTS idx_cmdhist_created_at ON command_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cmdhist_intent ON command_history(intent);
CREATE INDEX IF NOT EXISTS idx_cmdhist_status ON command_history(status);
