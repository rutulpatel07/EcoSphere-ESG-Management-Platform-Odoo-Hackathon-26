"""SQLAlchemy ORM models mirroring backend/db/schema.sql exactly.

Import every model module here so all tables register on ``Base.metadata``
before any relationship/ForeignKey string lookup is resolved.
"""

from app.models.base import Base
from app.models.category import Category
from app.models.department import Department
from app.models.enums import (
    CategoryType,
    ChallengeLifecycle,
    DataTier,
    OpType,
    UserRole,
)
from app.models.environmental import (
    CarbonTransaction,
    EmissionFactor,
    EnvironmentalGoal,
    OperationalRecord,
    ProductESGProfile,
)
from app.models.gamification import (
    Badge,
    Challenge,
    ChallengeParticipation,
    PointTransaction,
    Reward,
    RewardRedemption,
    UserBadge,
)
from app.models.governance import (
    Audit,
    ComplianceIssue,
    ESGLedger,
    ESGPolicy,
    PolicyAcknowledgement,
)
from app.models.misc import DepartmentScore, Notification, Settings
from app.models.social import CSRActivity, EmployeeParticipation
from app.models.user import User

__all__ = [
    "Base",
    "Category",
    "CategoryType",
    "Department",
    "ChallengeLifecycle",
    "DataTier",
    "OpType",
    "UserRole",
    "CarbonTransaction",
    "EmissionFactor",
    "EnvironmentalGoal",
    "OperationalRecord",
    "ProductESGProfile",
    "Badge",
    "Challenge",
    "ChallengeParticipation",
    "PointTransaction",
    "Reward",
    "RewardRedemption",
    "UserBadge",
    "Audit",
    "ComplianceIssue",
    "ESGLedger",
    "ESGPolicy",
    "PolicyAcknowledgement",
    "DepartmentScore",
    "Notification",
    "Settings",
    "CSRActivity",
    "EmployeeParticipation",
    "User",
]
