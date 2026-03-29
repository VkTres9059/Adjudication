from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ADJUDICATOR = "adjudicator"
    REVIEWER = "reviewer"
    AUDITOR = "auditor"


class ClaimStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    DUPLICATE = "duplicate"
    PENDED = "pended"
    MANAGERIAL_HOLD = "managerial_hold"
    PENDING_REVIEW = "pending_review"
    PENDING_ELIGIBILITY = "pending_eligibility"


class ClaimType(str, Enum):
    MEDICAL = "medical"
    DENTAL = "dental"
    VISION = "vision"
    HEARING = "hearing"


class DuplicateType(str, Enum):
    EXACT = "exact"
    NEAR = "near"
    LINE_LEVEL = "line_level"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
