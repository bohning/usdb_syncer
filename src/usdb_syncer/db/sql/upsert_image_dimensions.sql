INSERT INTO
    image_dimensions(sync_meta_id, kind, width, height)
VALUES
    (:sync_meta_id, :kind, :width, :height)
ON CONFLICT (sync_meta_id, kind) DO UPDATE
SET
    width = :width,
    height = :height
