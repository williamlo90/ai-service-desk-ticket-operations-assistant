CREATE TABLE IF NOT EXISTS sd_case_intake (
    tenant_id text NOT NULL,
    case_id uuid NOT NULL,
    actor_id text NOT NULL,
    idempotency_key text NOT NULL,
    intake jsonb NOT NULL CHECK (jsonb_typeof(intake) = 'object'),
    created_at timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, case_id),
    UNIQUE (tenant_id, actor_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS sd_journey (
    tenant_id text NOT NULL,
    case_id uuid NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    state jsonb NOT NULL CHECK (jsonb_typeof(state) = 'object'),
    PRIMARY KEY (tenant_id, case_id),
    CHECK (state->>'tenant' = tenant_id),
    CHECK (state->>'id' = case_id::text),
    CHECK ((state->>'revision')::bigint = revision)
);

CREATE TABLE IF NOT EXISTS sd_audit (
    tenant_id text NOT NULL,
    case_id uuid NOT NULL,
    sequence bigint NOT NULL,
    event jsonb NOT NULL,
    PRIMARY KEY (tenant_id, case_id, sequence),
    FOREIGN KEY (tenant_id, case_id) REFERENCES sd_journey(tenant_id, case_id)
);

CREATE OR REPLACE FUNCTION sd_reject_audit_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Audit events are append only';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER sd_audit_append_only BEFORE UPDATE OR DELETE ON sd_audit
    FOR EACH ROW EXECUTE FUNCTION sd_reject_audit_mutation();

ALTER TABLE sd_case_intake ENABLE ROW LEVEL SECURITY;
ALTER TABLE sd_case_intake FORCE ROW LEVEL SECURITY;
CREATE POLICY sd_intake_tenant ON sd_case_intake
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE sd_journey ENABLE ROW LEVEL SECURITY;
ALTER TABLE sd_journey FORCE ROW LEVEL SECURITY;
CREATE POLICY sd_journey_tenant ON sd_journey
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE sd_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE sd_audit FORCE ROW LEVEL SECURITY;
CREATE POLICY sd_audit_tenant ON sd_audit
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
