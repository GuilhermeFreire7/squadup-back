from enum import StrEnum


class Sport(StrEnum):
    FOOTBALL = "football"
    VOLLEYBALL = "volleyball"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    FUTSAL = "futsal"
    OTHER = "other"


class ExperienceLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MatchStatus(StrEnum):
    OPEN = "open"
    FULL = "full"
    PENDING_APPROVAL = "pending_approval"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ParticipationStatus(StrEnum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class MessageType(StrEnum):
    MESSAGE = "message"
    SYSTEM = "system"


class ReportReason(StrEnum):
    BAD_BEHAVIOR = "bad_behavior"
    VIOLENCE = "violence"
    NO_SHOW = "no_show"
    HATE_SPEECH = "hate_speech"
    SPAM = "spam"
    FAKE_INFO = "fake_info"
    OTHER = "other"


class ReportStatus(StrEnum):
    PENDING = "pending"
    ARCHIVED = "archived"
    WARNED = "warned"
    BANNED = "banned"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
