from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import IO, Any, Mapping, Optional, Sequence, Union

from . import queries
from ._core import GRAPHQL, LOGIN, PHOTOS, Flow, Op
from .enums import ROTATIONS, AdTab, ContactType, PropertyKind
from .errors import (
    APIError,
    AuthenticationError,
    BannedError,
    InvalidRequestError,
    MutationError,
    NotFoundError,
    UnconfirmedError,
)
from .messages import text
from .models import (
    Ad,
    AdPage,
    Category,
    CodeSent,
    ContactTypeInfo,
    Deleted,
    DeleteReason,
    Login,
    Option,
    Photo,
    Region,
    User,
)
from .session import gid, legacy_id

OPERATORS = ("10", "50", "51", "55", "60", "70", "77", "99")
PAGE_MAX = 100
BODY_MAX = 5000
TITLE_MAX = 100

PropertyValue = Union[str, int, float, bool]
PhotoSource = Union[bytes, bytearray, str, Path, IO[bytes]]
TabLike = Union[AdTab, str]
ContactLike = Union[ContactType, str]


def required(value: Any, name: str, limit: int = 255) -> str:
    result = str(value if value is not None else "").strip()
    if not result:
        raise InvalidRequestError(text("value.empty", field=name))
    if len(result) > limit:
        raise InvalidRequestError(text("value.too_long", field=name, limit=limit))
    return result


def whole(value: Any, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise InvalidRequestError(text("value.range", field=name, low=low, high=high, value=value))
    return value


def plain_id(value: Any, name: str) -> str:
    result = required(value, name, 200)
    if "/" in result or "?" in result or " " in result:
        raise InvalidRequestError(text("value.id", field=name, value=value))
    return result


def local_phone(raw: Any) -> str:
    digits = "".join(ch for ch in str(raw or "") if ch.isdigit())
    if digits.startswith("994"):
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 9 or not digits.startswith(OPERATORS):
        raise InvalidRequestError(text("value.phone", value=raw))
    return "0" + digits


def contact_phones(values: Optional[Sequence[str]]) -> Optional[list[str]]:
    if values is None:
        return None
    if isinstance(values, str):
        values = [values]
    if not 1 <= len(values) <= 3:
        raise InvalidRequestError(text("value.range", field="phones", low=1, high=3, value=len(values)))
    out = []
    for raw in values:
        digits = "".join(ch for ch in str(raw) if ch.isdigit())
        if not 9 <= len(digits) <= 12:
            raise InvalidRequestError(text("value.contact_phone", value=raw))
        out.append(str(raw).strip())
    return out


def contact_kind(value: ContactLike) -> str:
    given = value.value if isinstance(value, ContactType) else str(value).strip().upper()
    try:
        return ContactType(given).value
    except ValueError:
        raise InvalidRequestError(text("value.choice", field="contact_type", choices=[c.value for c in ContactType],
                                       value=value)) from None


def tab(value: Optional[TabLike]) -> Optional[str]:
    if value is None:
        return None
    try:
        return AdTab(str(value.value if isinstance(value, AdTab) else value).upper()).value
    except ValueError:
        raise InvalidRequestError(text("value.choice", field="status", choices=[t.value for t in AdTab],
                                       value=value)) from None


def read_photo(photo: PhotoSource, filename: Optional[str], content_type: Optional[str]) -> tuple[str, bytes, str]:
    if isinstance(photo, (bytes, bytearray)):
        name, content = filename or "photo.jpg", bytes(photo)
    elif isinstance(photo, (str, Path)):
        path = Path(photo)
        name, content = filename or path.name, path.read_bytes()
    elif hasattr(photo, "read"):
        data = photo.read()
        if not isinstance(data, (bytes, bytearray)):
            raise InvalidRequestError(text("value.photo", value=photo))
        name, content = filename or Path(str(getattr(photo, "name", "photo.jpg"))).name, bytes(data)
    else:
        raise InvalidRequestError(text("value.photo", value=photo))
    if not content:
        raise InvalidRequestError(text("value.empty", field="photo"))
    guessed = content_type or mimetypes.guess_type(name)[0] or "image/jpeg"
    return name, content, guessed


def unwrap(data: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    payload = data.get(field)
    if not isinstance(payload, Mapping):
        raise AuthenticationError(text("error.session"), status_code=200, body=dict(data))
    errors = [e for e in payload.get("errors") or [] if isinstance(e, Mapping)]
    if not errors:
        return payload
    detail = "; ".join(f"{'.'.join(map(str, e.get('path') or [])) or 'ad'}: {e.get('message')}" for e in errors)
    codes = {str(e.get("code") or (e.get("extensions") or {}).get("code") or "").upper() for e in errors}
    args: dict[str, Any] = {"errors": errors, "status_code": 200, "body": dict(payload)}
    if "USER_BANNED_ERROR" in codes:
        raise BannedError(text("error.banned", details=detail), **args)
    if "UNCONFIRMED" in codes:
        raise UnconfirmedError(text("error.unconfirmed", details=detail), **args)
    if "NOT_FOUND_ERROR" in codes:
        raise NotFoundError(text("error.mutation", details=detail), status_code=200, body=dict(payload))
    raise MutationError(text("error.mutation", details=detail), **args)


class _Resource:
    def __init__(self, client: Any) -> None:
        self._client = client

    @property
    def _settings(self) -> Any:
        return self._client.settings

    def _run(self, op: Op) -> Any:
        return self._client._run(op)

    def _flow(self, flow: Flow[Any]) -> Any:
        return self._client._flow(flow)

    def _site(self) -> str:
        return str(self._settings.site_url)

    def _me_op(self) -> Op:
        return Op(GRAPHQL, _current_user, query=queries.CURRENT_USER, operation="CurrentUser", safe=True, auth=True)


def _current_user(data: Mapping[str, Any]) -> User:
    user = data.get("currentUser")
    if not isinstance(user, Mapping) or not user.get("id"):
        raise AuthenticationError(text("error.session"), status_code=200, body=dict(data))
    return User.from_api(user)


class Auth(_Resource):
    def send_code(self, phone: str) -> Any:
        number = local_phone(phone)
        op = Op(LOGIN, endpoint="send_code", json={"phone": number}, unknown="error.unknown_code")
        op.parse = lambda body: CodeSent(
            phone=number,
            code_requests_left=body.get("code_requests_left") if isinstance(body.get("code_requests_left"), int)
            else None,
            retried=op.attempts > 1,
            note=text("note.retried_send") if op.attempts > 1 else None,
        )
        return self._run(op)

    def verify(self, phone: str, code: str) -> Any:
        return self._flow(self._verify(local_phone(phone), required(code, "code", 12)))

    def _verify(self, number: str, code: str) -> Flow[Login]:
        return_to = base64.b64encode(self._settings.return_to.encode()).decode()
        token: str = yield Op(LOGIN, _access_token, endpoint="verify_code", unknown="error.unknown_verify",
                              json={"phone": number, "code": code, "return_to": return_to})
        self._client.forget_session()
        yield Op(GRAPHQL, _login_payload, query=queries.LOGIN, operation="LoginUser",
                 variables={"accessToken": token}, capture=True)
        if not self._client.signed_in:
            raise APIError(text("error.no_cookie"), status_code=200)
        user: User = yield self._me_op()
        return Login(user=user, cookie=self._client.cookie)

    def me(self) -> Any:
        return self._run(self._me_op())


def _access_token(body: Mapping[str, Any]) -> str:
    token = body.get("access_token")
    if not token:
        raise APIError(text("error.no_token"), status_code=200, body=dict(body))
    return str(token)


def _login_payload(data: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = data.get("loginUser")
    payload = payload if isinstance(payload, Mapping) else {}
    errors = [e for e in payload.get("errors") or [] if isinstance(e, Mapping)]
    if errors or not payload.get("entity"):
        detail = "; ".join(str(e.get("message")) for e in errors) or "no entity"
        raise MutationError(text("error.login_refused", details=detail), errors=errors, status_code=200,
                            body=dict(payload))
    return payload


class Catalog(_Resource):
    def categories(self) -> Any:
        return self._run(Op(GRAPHQL, _categories, query=queries.CATEGORIES, operation="Categories", safe=True))

    def category(self, category_id: Union[str, int]) -> Any:
        return self._run(self._category_op(plain_id(category_id, "category_id")))

    def _category_op(self, category_id: str) -> Op:
        def parse(data: Mapping[str, Any]) -> Category:
            node = data.get("node")
            if not isinstance(node, Mapping) or not node.get("legacyResourceId"):
                raise InvalidRequestError(text("ad.unknown_category", category_id=category_id))
            return Category.from_api(node)

        return Op(GRAPHQL, parse, query=queries.CATEGORY_NODE, operation="Category",
                  variables={"id": gid("Category", category_id)}, safe=True)

    def property_options(self, parent_option_id: Union[str, int]) -> Any:
        return self._run(self._options_op(plain_id(parent_option_id, "parent_option_id")))

    def _options_op(self, parent: str) -> Op:
        parse = lambda data: tuple(Option.from_api(o) for o in data.get("propertyOptions") or []
                                   if isinstance(o, Mapping))
        return Op(GRAPHQL, parse, query=queries.PROPERTY_OPTIONS, operation="PropertyOptions",
                  variables={"p": parent}, safe=True)

    def regions(self) -> Any:
        parse = lambda data: tuple(Region.from_api(r) for r in data.get("regions") or [] if isinstance(r, Mapping))
        return self._run(Op(GRAPHQL, parse, query=queries.REGIONS, operation="Regions", safe=True))

    def contact_types(self) -> Any:
        parse = lambda data: tuple(ContactTypeInfo.from_api(t)
                                   for t in (data.get("formElements") or {}).get("contactTypes") or []
                                   if isinstance(t, Mapping))
        return self._run(Op(GRAPHQL, parse, query=queries.CONTACT_TYPES, operation="ContactTypes", safe=True))


def _categories(data: Mapping[str, Any]) -> tuple[Category, ...]:
    return tuple(Category.from_api(c) for c in data.get("categories") or [] if isinstance(c, Mapping))


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _fmt(value: Optional[float]) -> str:
    return "" if value is None else f"{value:g}"


class Ads(_Resource):
    def _property_set(self, category_id: str, values: Mapping[str, PropertyValue], *, price: Optional[float],
                      photo_ids: Sequence[str], title: Optional[str]) -> Flow[dict[str, Any]]:
        category: Category = yield self._client.catalog._category_op(category_id)
        if not category.leaf:
            raise InvalidRequestError(text("ad.leaf", category_id=category_id))
        errors: list[dict[str, str]] = []
        props = {p.id: p for p in category.properties}
        for key in values:
            if key not in props:
                errors.append({"field": f"properties.{key}", "error": text("ad.unknown_property")})
        active = {key for key, p in props.items() if not p.depends_on}
        changed = True
        while changed:
            changed = False
            for key in list(active):
                p = props[key]
                if p.kind != PropertyKind.COLLECTION or key not in values:
                    continue
                chosen = p.option(values[key])
                for child in chosen.enables if chosen else ():
                    if child in props and child not in active:
                        active.add(child)
                        changed = True
        for key in list(active):
            hidden = props[key].hidden_when
            if hidden and str(values.get(hidden.property)) in hidden.options:
                active.discard(key)
        out: dict[str, list[dict[str, Any]]] = {"collection": [], "range": [], "boolean": []}
        for key, p in props.items():
            field = f"properties.{key}"
            name = p.name or key
            if key not in values:
                if key in active and p.required:
                    errors.append({"field": field, "error": text("ad.required", name=name)})
                continue
            if key not in active:
                errors.append({"field": field, "error": text("ad.inactive", name=name, parent=p.depends_on)})
                continue
            value = values[key]
            if p.kind == PropertyKind.COLLECTION:
                if isinstance(value, bool):
                    errors.append({"field": field, "error": text("ad.option_id")})
                    continue
                ids = {o.id for o in p.options}
                if p.depends_on:
                    options: tuple[Option, ...] = yield self._client.catalog._options_op(str(values.get(p.depends_on)))
                    ids = {o.id for o in options if o.property_id == key}
                if str(value) not in ids:
                    errors.append({"field": field, "error": text("ad.not_option", value=value, name=name,
                                                                 valid=sorted(ids))})
                    continue
                out["collection"].append({"legacyId": key, "value": str(value)})
            elif p.kind == PropertyKind.RANGE:
                number = _number(value)
                if number is None:
                    errors.append({"field": field, "error": text("ad.number", name=name)})
                    continue
                if (p.min is not None and number < p.min) or (p.max is not None and number > p.max):
                    errors.append({"field": field, "error": text("ad.between", name=name, low=_fmt(p.min),
                                                                 high=_fmt(p.max))})
                    continue
                out["range"].append({"legacyId": key, "value": number})
            elif p.kind == PropertyKind.BOOLEAN:
                if not isinstance(value, bool):
                    errors.append({"field": field, "error": text("ad.boolean", name=name)})
                    continue
                out["boolean"].append({"legacyId": key, "value": value})
            elif p.kind == PropertyKind.STRING:
                written = str(value).strip()
                if not written or isinstance(value, bool):
                    errors.append({"field": field, "error": text("ad.text", name=name)})
                    continue
                out["collection"].append({"legacyId": key, "value": written})
            else:
                errors.append({"field": field, "error": text("ad.unsupported", kind=p.raw.get("type"))})
        if category.price_required and price is None:
            errors.append({"field": "price", "error": text("ad.price")})
        if category.photo_required and not photo_ids:
            errors.append({"field": "photo_ids", "error": text("ad.photos")})
        if category.title_required and not (title or "").strip():
            errors.append({"field": "title", "error": text("ad.title")})
        if errors:
            raise InvalidRequestError(text("ad.invalid", details="; ".join(f"{e['field']}: {e['error']}"
                                                                           for e in errors)), errors=errors)
        return {k: v for k, v in out.items() if v}

    @staticmethod
    def _clean(category_id: Any, body: Any, title: Optional[str], price: Optional[float],
               properties: Optional[Mapping[Any, PropertyValue]], photo_ids: Optional[Sequence[str]]
               ) -> tuple[str, str, Optional[str], Optional[float], dict[str, PropertyValue], list[str]]:
        category = plain_id(category_id, "category_id")
        text_body = required(body, "body", BODY_MAX)
        heading = required(title, "title", TITLE_MAX) if title is not None and str(title).strip() else None
        if price is not None and (isinstance(price, bool) or _number(price) is None or float(price) <= 0):
            raise InvalidRequestError(text("value.price", value=price))
        values = {str(k).strip(): v for k, v in (properties or {}).items()}
        photos = [required(p, "photo_ids", 500) for p in (photo_ids or [])]
        return category, text_body, heading, (float(price) if price is not None else None), values, photos

    def validate(self, category_id: Union[str, int], body: str, *, properties: Optional[Mapping[Any, PropertyValue]]
                 = None, price: Optional[float] = None, title: Optional[str] = None,
                 photo_ids: Optional[Sequence[str]] = None) -> Any:
        category, _, heading, amount, values, photos = self._clean(category_id, body, title, price, properties,
                                                                   photo_ids)
        return self._flow(self._property_set(category, values, price=amount, photo_ids=photos, title=heading))

    def create(
        self,
        category_id: Union[str, int],
        body: str,
        *,
        properties: Optional[Mapping[Any, PropertyValue]] = None,
        price: Optional[float] = None,
        title: Optional[str] = None,
        region_id: Union[str, int, None] = None,
        photo_ids: Optional[Sequence[str]] = None,
        contact_type: ContactLike = ContactType.CALLS_AND_MESSAGES,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phones: Optional[Sequence[str]] = None,
    ) -> Any:
        category, text_body, heading, amount, values, photos = self._clean(category_id, body, title, price,
                                                                           properties, photo_ids)
        region = plain_id(region_id if region_id is not None else self._settings.default_region, "region_id")
        contact = {"contactType": contact_kind(contact_type), "name": name,
                   "email": email, "phones": contact_phones(phones)}
        if name is not None:
            contact["name"] = required(name, "name", 100)
        if email is not None:
            contact["email"] = str(email).strip()[:255]
        return self._flow(self._create(category, text_body, heading, amount, values, photos, region, contact))

    def _create(self, category: str, body: str, title: Optional[str], price: Optional[float],
                values: dict[str, PropertyValue], photos: list[str], region: str,
                contact: dict[str, Any]) -> Flow[Ad]:
        property_set = yield from self._property_set(category, values, price=price, photo_ids=photos, title=title)
        phones, email = contact["phones"], contact["email"]
        if not phones or email is None:
            user: User = yield self._me_op()
            phones = phones or ([user.phone] if user.phone else None)
            email = email if email is not None else (user.email or "")
        if not phones:
            raise InvalidRequestError(text("ad.phone"), errors=[{"field": "phones", "error": "required"}])
        if not (email or "").strip():
            raise InvalidRequestError(text("ad.email"), errors=[{"field": "email", "error": "required"}])
        contact_in: dict[str, Any] = {"contactType": contact["contactType"], "email": email, "phones": phones}
        if contact.get("name"):
            contact_in["name"] = contact["name"]
        params: dict[str, Any] = {
            "categoryId": gid("Category", category),
            "regionId": gid("Region", region),
            "source": self._settings.source,
            "body": body,
            "photoIds": photos,
            "propertySet": property_set,
            "contactAttributes": contact_in,
        }
        if title:
            params["title"] = title
        if price is not None:
            params["price"] = price
        site = self._site()
        ad: Ad = yield Op(GRAPHQL, lambda data: Ad.from_api(unwrap(data, "createAd").get("entity") or {}, site),
                          query=queries.CREATE_AD, operation="CreateAd", variables={"p": params}, auth=True)
        return ad

    def update(
        self,
        ad_id: Union[str, int],
        category_id: Union[str, int],
        body: str,
        *,
        properties: Optional[Mapping[Any, PropertyValue]] = None,
        price: Optional[float] = None,
        title: Optional[str] = None,
        photo_ids: Optional[Sequence[str]] = None,
        contact_type: ContactLike = ContactType.CALLS_AND_MESSAGES,
    ) -> Any:
        ad = plain_id(ad_id, "ad_id")
        category, text_body, heading, amount, values, photos = self._clean(category_id, body, title, price,
                                                                           properties, photo_ids)
        kind = contact_kind(contact_type)
        return self._flow(self._update(ad, category, text_body, heading, amount, values, photos, kind))

    def _update(self, ad_id: str, category: str, body: str, title: Optional[str], price: Optional[float],
                values: dict[str, PropertyValue], photos: list[str], kind: str) -> Flow[Ad]:
        property_set = yield from self._property_set(category, values, price=price, photo_ids=photos, title=title)
        params: dict[str, Any] = {
            "body": body,
            "contactType": kind,
            "photoIds": photos,
            "propertySet": {"boolean": property_set["boolean"]} if property_set.get("boolean") else {},
        }
        if price is not None:
            params["price"] = price
        site = self._site()

        def parse(data: Mapping[str, Any]) -> Ad:
            found = Ad.from_api(unwrap(data, "updateAd").get("entity") or {}, site)
            return found if found.id else found.model_copy(update={"id": ad_id})

        ad: Ad = yield Op(GRAPHQL, parse, query=queries.UPDATE_AD, operation="UpdateAd",
                          variables={"id": gid("Ad", ad_id), "source": self._settings.source, "p": params}, auth=True)
        return ad

    def delete_reasons(self, ad_id: Union[str, int]) -> Any:
        return self._run(self._reasons_op(plain_id(ad_id, "ad_id")))

    def _reasons_op(self, ad_id: str) -> Op:
        parse = lambda data: tuple(DeleteReason.from_api(r) for r in (data.get("ad") or {}).get("deleteReasons") or []
                                   if isinstance(r, Mapping))
        return Op(GRAPHQL, parse, query=queries.DELETE_REASONS, operation="DeleteReasons", variables={"id": ad_id},
                  safe=True, auth=True, missing=text("ad.not_found", ad_id=ad_id))

    def delete(self, ad_id: Union[str, int], reason_id: Union[str, int, None] = None) -> Any:
        ad = plain_id(ad_id, "ad_id")
        reason = plain_id(reason_id, "reason_id") if reason_id is not None else None
        return self._flow(self._delete(ad, reason))

    def _delete(self, ad_id: str, reason_id: Optional[str]) -> Flow[Deleted]:
        reasons: tuple[DeleteReason, ...] = yield self._reasons_op(ad_id)
        usable = [r for r in reasons if not r.description_required]
        if reason_id is not None:
            chosen = next((r for r in usable if reason_id in (r.id, r.legacy_id)), None)
            if chosen is None:
                raise InvalidRequestError(text("ad.delete_reason", reason=reason_id, ad_id=ad_id))
        else:
            if not usable:
                raise InvalidRequestError(text("ad.no_delete", ad_id=ad_id))
            chosen = next((r for r in usable if r.legacy_id == self._settings.delete_reason), usable[0])
        done: bool = yield Op(GRAPHQL, lambda data: bool(unwrap(data, "destroyAd").get("entity")),
                              query=queries.DESTROY_AD, operation="DestroyAd", auth=True,
                              variables={"id": gid("Ad", ad_id), "reason": chosen.id,
                                         "source": self._settings.source})
        return Deleted(ad_id=ad_id, deleted=done, reason=chosen.name)

    def prolong(self, ad_id: Union[str, int]) -> Any:
        ad = plain_id(ad_id, "ad_id")
        return self._run(Op(GRAPHQL, lambda data: bool(unwrap(data, "prolongAds").get("entity")),
                            query=queries.PROLONG_ADS, operation="ProlongAds", variables={"ids": [gid("Ad", ad)]},
                            auth=True))

    def get(self, ad_id: Union[str, int]) -> Any:
        ad = plain_id(ad_id, "ad_id")
        site = self._site()

        def parse(data: Mapping[str, Any]) -> Ad:
            found = data.get("ad")
            if not isinstance(found, Mapping):
                raise NotFoundError(text("ad.not_found", ad_id=ad), status_code=200, body=dict(data))
            return Ad.from_api(found, site)

        return self._run(Op(GRAPHQL, parse, query=queries.AD, operation="Ad", variables={"id": ad}, safe=True,
                            auth=True, missing=text("ad.not_found", ad_id=ad)))

    def list(self, status: Optional[TabLike] = None, first: int = 20, after: Optional[str] = None) -> Any:
        return self._run(self._page_op(tab(status), whole(first, "first", 1, PAGE_MAX), after))

    def _page_op(self, status: Optional[str], first: int, after: Optional[str]) -> Op:
        site = self._site()

        def parse(data: Mapping[str, Any]) -> AdPage:
            conn = data.get("currentUserAds")
            if not isinstance(conn, Mapping):
                raise AuthenticationError(text("error.session"), status_code=200, body=dict(data))
            return AdPage.from_api(conn, site)

        return Op(GRAPHQL, parse, query=queries.MY_ADS, operation="MyAds", safe=True, auth=True,
                  variables={"status": status, "first": first, "after": after})

    def all(self, status: Optional[TabLike] = None, page_size: int = 50, max_pages: int = 50) -> Any:
        return self._flow(self._every(tab(status), whole(page_size, "page_size", 1, PAGE_MAX), max(1, max_pages)))

    def _every(self, status: Optional[str], size: int, pages: int) -> Flow[tuple[Ad, ...]]:
        items: list[Ad] = []
        cursor: Optional[str] = None
        for _ in range(pages):
            page: AdPage = yield self._page_op(status, size, cursor)
            items.extend(page.items)
            cursor = page.next_cursor
            if not cursor:
                break
        return tuple(items)


class Photos(_Resource):
    def upload(self, photo: PhotoSource, filename: Optional[str] = None, content_type: Optional[str] = None) -> Any:
        name, content, ctype = read_photo(photo, filename, content_type)
        return self._run(Op(PHOTOS, _photo_upload, endpoint="photo_upload", params={"lang": self._settings.language},
                            files=[("images[]", (name, content, ctype))], safe=True, auth=True))

    def rotate(self, photo_id: str, angle: int = 90) -> Any:
        if angle not in ROTATIONS or isinstance(angle, bool):
            raise InvalidRequestError(text("value.angle", value=angle))
        params = {"id": required(photo_id, "photo_id", 500), "angle": str(angle), "lang": self._settings.language}
        return self._run(Op(PHOTOS, _photo_rotate, endpoint="photo_rotate", params=params, safe=True, auth=True))


def _photo_upload(body: Mapping[str, Any]) -> Photo:
    photos = body.get("photos") or []
    first = photos[0] if photos and isinstance(photos[0], Mapping) else {}
    if first.get("id") in (None, ""):
        raise APIError(text("error.photo_id"), status_code=200, body=dict(body))
    return Photo.from_api(first)


def _photo_rotate(body: Mapping[str, Any]) -> Photo:
    if body.get("id") in (None, ""):
        raise APIError(text("error.photo_id"), status_code=200, body=dict(body))
    return Photo.from_api(body)


__all__ = ["Auth", "Catalog", "Ads", "Photos", "legacy_id", "local_phone"]
