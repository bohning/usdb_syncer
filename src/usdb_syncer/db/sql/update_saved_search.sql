WITH RECURSIVE candidates AS (
    SELECT
        :new_name AS name,
        0 AS suffix
    UNION
    ALL
    SELECT
        :new_name || ' (' || (suffix + 1) || ')' AS name,
        suffix + 1 AS suffix
    FROM
        candidates
    WHERE
        name != :old_name
        AND name IN (
            SELECT
                name
            FROM
                saved_search
        )
)
UPDATE
    saved_search
SET
    name = (
        SELECT
            name
        FROM
            candidates
        ORDER BY
            suffix DESC
        LIMIT
            1
    ), search = json(:search), is_default = :is_default, subscribed = :subscribed
WHERE
    name = :old_name RETURNING name;