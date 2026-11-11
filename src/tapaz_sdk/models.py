from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import GRAPHQL_KINDS, AdStatus, ContactType, PropertyKind
from .session import legacy_id


def _pick(body: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = body.get(key)
        if value is not None and value != "":
            return value
    return None


def _str(body: Mapping[str, Any], *keys: str) -> Optional[str]:
    value = _pick(body, *keys)
    return None if value is None else str(value)


def _float(body: Mapping[str, Any], *keys: str) -> Optional[float]:
    value = _pick(body, *keys)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(body: Mapping[str, Any], *keys: str) -> Optional[int]:
    value = _float(body, *keys)
    return None if value is None else int(value)


def _when(body: Mapping[str, Any], *keys: str) -> Optional[datetime]:
    value = _pick(body, *keys)
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def absolute(site_url: str, path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http"):
        return path
    return site_url.rstrip("/") + ("" if path.startswith("/") else "/") + path


class Model(BaseModel):
    model_config = ConfigDict(frozen=True)


class User(Model):
    id: Optional[str]
    global_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_confirmed: Optional[bool] = None
    is_shop: bool = False
    shop: Optional[str] = None
    banned: bool = False
    raw: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> User:
        confirmed = body.get("isPhoneConfirmed")
        return cls(
            id=_str(body, "legacyId") or legacy_id(body.get("id")),
            global_id=_str(body, "id"),
            name=_str(body, "name"),
            email=_str(body, "email"),
            phone=_str(body, "phone", "authenticationPhone"),
            phone_confirmed=confirmed if isinstance(confirmed, bool) else None,
            is_shop=body.get("isShop") is True,
            shop=_str(_map(body.get("shop")), "name"),
            banned=body.get("isBanned") is True,
            raw=dict(body),
        )


class Option(Model):
    id: str
    name: Optional[str] = None
    enables: tuple[str, ...] = ()
    property_id: Optional[str] = None

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Option:
        return cls(
            id=str(body.get("legacyResourceId")),
            name=_str(body, "name"),
            enables=tuple(str(x) for x in _list(body.get("childrenPropertyIds"))),
            property_id=_str(body, "propertyLegacyId"),
        )


class HiddenWhen(Model):
    property: str
    options: tuple[str, ...] = ()


class Property(Model):
    id: str
    name: str
    kind: PropertyKind
    required: bool = False
    editable: bool = False
    depends_on: Optional[str] = None
    unit: Optional[str] = None
    hint: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    hidden_when: Optional[HiddenWhen] = None
    options: tuple[Option, ...] = ()
    raw: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Property:
        settings = _map(body.get("settings"))
        hidden = _map(body.get("hiddenWhen"))
        return cls(
            id=str(body.get("legacyResourceId")),
            name=str(body.get("name") or "").strip(),
            kind=GRAPHQL_KINDS.get(str(body.get("type")), PropertyKind.OTHER),
            required=body.get("isRequired") is True,
            editable=body.get("allowEdit") is True,
            depends_on=_str(body, "parentLegacyId"),
            unit=_str(body, "measurementUnits"),
            hint=_str(body, "hint"),
            min=_float(settings, "from"),
            max=_float(settings, "to"),
            step=_float(settings, "step"),
            hidden_when=HiddenWhen(property=str(hidden["propertyLegacyId"]),
                                   options=tuple(str(x) for x in _list(hidden.get("optionLegacyIds"))))
            if hidden.get("propertyLegacyId") else None,
            options=tuple(Option.from_api(o) for o in _list(body.get("options")) if isinstance(o, Mapping)),
            raw=dict(body),
        )

    def option(self, option_id: object) -> Optional[Option]:
        return next((o for o in self.options if o.id == str(option_id)), None)


class Category(Model):
    id: str
    name: Optional[str] = None
    path: Optional[str] = None
    leaf: bool = True
    photo_required: bool = False
    price_required: bool = False
    title_required: bool = False
    free_limit: Optional[int] = None
    warning: Optional[str] = None
    children: tuple[Category, ...] = ()
    properties: tuple[Property, ...] = ()
    raw: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Category:
        return cls(
            id=str(body.get("legacyResourceId")),
            name=_str(body, "name"),
            path=_str(body, "path"),
            leaf=not body.get("hasChildren"),
            photo_required=body.get("isPhotoRequiredOnCreate") is True,
            price_required=body.get("isPriceRequired") is True,
            title_required=not body.get("hasAutogeneratedTitle"),
            free_limit=_int(body, "freeLimit"),
            warning=_str(body, "warningMessage"),
            children=tuple(cls.from_api(c) for c in _list(body.get("children")) if isinstance(c, Mapping)),
            properties=tuple(Property.from_api(p) for p in _list(body.get("properties")) if isinstance(p, Mapping)),
            raw=dict(body),
        )

    def walk(self) -> Iterator[Category]:
        yield self
        for child in self.children:
            yield from child.walk()

    def find_property(self, property_id: object) -> Optional[Property]:
        return next((p for p in self.properties if p.id == str(property_id)), None)


class Region(Model):
    id: str
    name: Optional[str] = None
    default: bool = False

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Region:
        return cls(id=str(body.get("legacyResourceId")), name=_str(body, "name"), default=body.get("default") is True)


class ContactTypeInfo(Model):
    id: str
    name: Optional[str] = None
    default: bool = False

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> ContactTypeInfo:
        return cls(id=str(body.get("enum")), name=_str(body, "name"), default=body.get("default") is True)

    @property
    def type(self) -> Optional[ContactType]:
        try:
            return ContactType(self.id)
        except ValueError:
            return None


class Ad(Model):
    id: Optional[str]
    global_id: Optional[str] = None
    title: Optional[str] = None
    status: AdStatus = AdStatus.UNKNOWN
    status_message: Optional[str] = None
    reject_reason: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None
    price: Optional[float] = None
    expires_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    thumbnail: Optional[str] = None
    is_author: Optional[bool] = None
    raw: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any], site_url: str = "https://tap.az") -> Ad:
        author = body.get("isAuthor")
        path = _str(body, "path")
        return cls(
            id=_str(body, "legacyResourceId") or legacy_id(body.get("id")),
            global_id=_str(body, "id"),
            title=_str(body, "title"),
            status=AdStatus.parse(body.get("status")),
            status_message=_str(body, "statusMessage"),
            reject_reason=_str(body, "rejectReason"),
            path=path,
            url=absolute(site_url, path),
            price=_float(body, "price"),
            expires_at=_when(body, "expiresAt"),
            updated_at=_when(body, "updatedAt"),
            thumbnail=_str(_map(body.get("photo")), "url"),
            is_author=author if isinstance(author, bool) else None,
            raw=dict(body),
        )


class AdPage(Model):
    items: tuple[Ad, ...] = ()
    total: Optional[int] = None
    next_cursor: Optional[str] = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None

    @classmethod
    def from_api(cls, body: Mapping[str, Any], site_url: str = "https://tap.az") -> AdPage:
        info = _map(body.get("pageInfo"))
        return cls(
            items=tuple(Ad.from_api(n, site_url) for n in _list(body.get("nodes")) if isinstance(n, Mapping)),
            total=_int(body, "totalCount"),
            next_cursor=_str(info, "endCursor") if info.get("hasNextPage") else None,
        )


class Photo(Model):
    id: str
    thumbnail_url: Optional[str] = None
    raw: Mapping[str, Any] = Field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> Photo:
        return cls(id=str(body.get("id")), thumbnail_url=_str(body, "thumbnail_url", "thumbnail", "url"),
                   raw=dict(body))


class CodeSent(Model):
    phone: str
    code_requests_left: Optional[int] = None
    retried: bool = False
    note: Optional[str] = None


class DeleteReason(Model):
    id: str
    legacy_id: Optional[str] = None
    name: Optional[str] = None
    description_required: bool = False

    @classmethod
    def from_api(cls, body: Mapping[str, Any]) -> DeleteReason:
        return cls(id=str(body.get("id")), legacy_id=legacy_id(body.get("id")), name=_str(body, "name"),
                   description_required=body.get("descriptionRequired") is True)


class Deleted(Model):
    ad_id: str
    deleted: bool
    reason: Optional[str] = None


class Login(Model):
    user: User
    cookie: str = Field(repr=False)
