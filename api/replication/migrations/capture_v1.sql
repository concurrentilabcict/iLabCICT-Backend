-- Frozen migration asset. No business data is changed by installing these functions.
CREATE OR REPLACE FUNCTION public.ilab_replication_order() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(73481001);
    RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION public.ilab_replication_no_truncate() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'TRUNCATE is unsupported on a replication capture table';
END $$;

CREATE OR REPLACE FUNCTION public.ilab_replication_capture() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public SET timezone = 'UTC' AS $$
DECLARE
    before_row jsonb;
    after_row jsonb;
    key_row jsonb;
BEGIN
    IF TG_TABLE_SCHEMA <> 'public' OR TG_TABLE_NAME LIKE 'replication_%' THEN
        RAISE EXCEPTION 'Invalid capture table';
    END IF;
    IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
        RETURN NULL;
    END IF;
    IF TG_OP <> 'INSERT' THEN before_row := to_jsonb(OLD); END IF;
    IF TG_OP <> 'DELETE' THEN after_row := to_jsonb(NEW); END IF;
    -- Discover the entire primary key, including composite and string keys.
    SELECT jsonb_object_agg(a.attname, COALESCE(before_row, after_row)->a.attname)
    INTO key_row
    FROM pg_index i
    JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, position)
        ON k.position <= i.indnkeyatts
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.attnum
    WHERE i.indrelid = TG_RELID AND i.indisprimary;
    IF key_row IS NULL THEN RAISE EXCEPTION 'Capture requires a primary key'; END IF;
    INSERT INTO public.replication_replicationevent
      (event_uuid, transaction_id, event_type, model_name, object_id, primary_key,
       payload, old_row, status, attempts, created_at, applied_at, last_error, next_retry_at)
    VALUES
      (gen_random_uuid(), pg_current_xact_id()::text, TG_OP, TG_TABLE_NAME, '', key_row,
       COALESCE(after_row, 'null'::jsonb), before_row, 'PENDING', 0, clock_timestamp(), NULL, NULL, NULL);
    RETURN NULL;
END $$;
