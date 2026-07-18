-- PostgreSQL initialization script
-- Runs once when the container first starts (before Alembic migrations)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
