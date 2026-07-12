"""Python mirrors of the Postgres enum types defined in backend/db/schema.sql.

The Postgres types already exist (created by schema.sql), so every column that
uses one of these must pass ``create_type=False`` to avoid SQLAlchemy trying to
issue a redundant ``CREATE TYPE`` when metadata is used for anything other than
reading/writing rows.
"""

import enum
from collections.abc import Iterable

from sqlalchemy import Enum as SAEnum


class CategoryType(str, enum.Enum):
    CSR = "CSR"
    CHALLENGE = "CHALLENGE"


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class OpType(str, enum.Enum):
    PURCHASE = "PURCHASE"
    MANUFACTURING = "MANUFACTURING"
    EXPENSE = "EXPENSE"
    FLEET = "FLEET"


class DataTier(str, enum.Enum):
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    DEFAULT = "DEFAULT"


class ChallengeLifecycle(str, enum.Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    UNDER_REVIEW = "UnderReview"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Build a SQLAlchemy Enum column type bound to an existing Postgres enum."""

    def _values(_: Iterable[enum.Enum]) -> list[str]:
        return [member.value for member in enum_cls]

    return SAEnum(enum_cls, name=name, values_callable=_values, create_type=False)
