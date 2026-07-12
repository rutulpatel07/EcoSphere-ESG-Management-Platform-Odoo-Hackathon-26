"""Leaderboard queries.

``individual_leaderboard`` matches docs/CONTRACT.md's
``GET /gamification/leaderboard`` shape exactly (the default response).
``department_leaderboard`` (per-capita XP ranking) is additive, reachable
via ``?scope=department`` — CONTRACT.md doesn't document it, so it's kept
behind a query param rather than changing the default documented shape.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session


def individual_leaderboard(db: Session, limit: int = 100) -> list[dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT u.id AS user_id, u.full_name AS user, d.name AS department,
                       COALESCE(SUM(pt.points), 0) AS points
                FROM users u
                LEFT JOIN departments d ON d.id = u.department_id
                LEFT JOIN point_transactions pt ON pt.user_id = u.id
                WHERE u.is_active = TRUE
                GROUP BY u.id, u.full_name, d.name
                ORDER BY points DESC, u.id
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )
    return [
        {
            "rank": i + 1,
            "user_id": row["user_id"],
            "user": row["user"],
            "department": row["department"],
            "points": int(row["points"]),
        }
        for i, row in enumerate(rows)
    ]


def department_leaderboard(db: Session) -> list[dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT d.id AS department_id, d.name AS department,
                       COALESCE(SUM(pt.points), 0) AS total_points,
                       COUNT(DISTINCT u.id) AS headcount
                FROM departments d
                JOIN users u ON u.department_id = d.id AND u.is_active = TRUE
                LEFT JOIN point_transactions pt ON pt.user_id = u.id
                GROUP BY d.id, d.name
                HAVING COUNT(DISTINCT u.id) > 0
                ORDER BY (COALESCE(SUM(pt.points), 0)::float / COUNT(DISTINCT u.id)) DESC
                """
            )
        )
        .mappings()
        .all()
    )
    result = []
    for i, row in enumerate(rows):
        per_capita = float(row["total_points"]) / row["headcount"]
        result.append(
            {
                "rank": i + 1,
                "department_id": row["department_id"],
                "department": row["department"],
                "total_points": int(row["total_points"]),
                "headcount": row["headcount"],
                "points_per_capita": round(per_capita, 2),
            }
        )
    return result
