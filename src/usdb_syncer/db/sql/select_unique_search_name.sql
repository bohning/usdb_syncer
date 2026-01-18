WITH RECURSIVE candidates AS (
    SELECT
        :new_name AS name,
        0 AS suffix
    UNION
    ALL
    SELECT
        :new_name || ' (' || (suffix + 1) || ')',
        suffix + 1
    FROM
        candidates
    WHERE
        name != :old_name
        AND candidates.name IN (
            SELECT
                name
            FROM
                saved_search
        )
)
SELECT
    name
FROM
    candidates
ORDER BY
    suffix DESC
LIMIT
    1;