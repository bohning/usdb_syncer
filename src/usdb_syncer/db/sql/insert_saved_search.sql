WITH RECURSIVE candidates AS (
    SELECT
        :name AS name,
        0 AS suffix
    UNION
    ALL
    SELECT
        :name || ' (' || (suffix + 1) || ')' AS name,
        suffix + 1 AS suffix
    FROM
        candidates
    WHERE
        candidates.name IN (
            SELECT
                name
            FROM
                saved_search
        )
)
INSERT INTO
    saved_search (name, search, is_default, subscribed)
SELECT
    name,
    json(:search),
    :is_default,
    :subscribed
FROM
    candidates
ORDER BY
    suffix DESC
LIMIT
    1 RETURNING name;