-- Roles for the habits database. Locally a superuser runs this; on Neon
-- `habits-db provision` creates the same roles through the migrator.
--
-- habits_migrator  owns the schema and runs migrations only.
-- habits_api       the API at runtime: no superuser, no BYPASSRLS, owns nothing.
-- habits_publisher sweeps and marks the outbox across workspaces; nothing else.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'habits_migrator') THEN
        CREATE ROLE habits_migrator LOGIN NOSUPERUSER NOCREATEROLE NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'habits_api') THEN
        CREATE ROLE habits_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'habits_publisher') THEN
        CREATE ROLE habits_publisher LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
    END IF;
END
$$;
