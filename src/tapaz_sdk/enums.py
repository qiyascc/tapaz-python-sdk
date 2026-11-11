from __future__ import annotations

from enum import Enum


class ContactType(str, Enum):
    CALLS_AND_MESSAGES = "CALLS_AND_MESSAGES"
    ONLY_CALLS = "ONLY_CALLS"
    ONLY_MESSAGES = "ONLY_MESSAGES"


class AdStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def parse(cls, value: object) -> AdStatus:
        try:
            return cls(str(value or "").upper())
        except ValueError:
            return cls.UNKNOWN

    @property
    def is_live(self) -> bool:
        return self in (AdStatus.APPROVED, AdStatus.PUBLISHED)


class AdTab(str, Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"


class PropertyKind(str, Enum):
    COLLECTION = "collection"
    RANGE = "range"
    BOOLEAN = "boolean"
    STRING = "string"
    OTHER = "other"


GRAPHQL_KINDS = {
    "CollectionProperty": PropertyKind.COLLECTION,
    "RangeProperty": PropertyKind.RANGE,
    "BooleanProperty": PropertyKind.BOOLEAN,
    "StringProperty": PropertyKind.STRING,
    "PhoneNumberProperty": PropertyKind.STRING,
}

ROTATIONS = (90, 180, 270)
