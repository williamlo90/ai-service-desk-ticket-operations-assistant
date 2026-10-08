#!/bin/sh
set -eu
# No shell tracing: these values must never reach stdout or command arguments.
export APP_PASSWORD="$(cat /run/secrets/db_app)"
export N8N_PASSWORD="$(cat /run/secrets/db_n8n)"
psql -v ON_ERROR_STOP=1 --username postgres --dbname postgres <<'SQL'
\getenv app_password APP_PASSWORD
\getenv n8n_password N8N_PASSWORD
CREATE ROLE service_desk_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'app_password';
CREATE ROLE service_desk_n8n LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'n8n_password';
CREATE DATABASE service_desk OWNER service_desk_app;
CREATE DATABASE n8n OWNER service_desk_n8n;
REVOKE CONNECT, TEMPORARY ON DATABASE postgres FROM PUBLIC;
REVOKE CONNECT, TEMPORARY ON DATABASE template1 FROM PUBLIC;
REVOKE ALL ON DATABASE service_desk FROM PUBLIC;
REVOKE ALL ON DATABASE n8n FROM PUBLIC;
\connect service_desk
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO service_desk_app;
CREATE EXTENSION vector;
\connect n8n
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO service_desk_n8n;
SQL
unset APP_PASSWORD N8N_PASSWORD
