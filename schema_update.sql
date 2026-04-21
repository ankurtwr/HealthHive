USE medcompare;

ALTER TABLE price_cache 
  ADD COLUMN medicine_name VARCHAR(300),
  ADD COLUMN pack_size VARCHAR(100),
  ADD COLUMN manufacturer VARCHAR(300);
 
 CREATE INDEX idx_cache_lookup 
ON price_cache(medicine_id, platform, fetched_at);