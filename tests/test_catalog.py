from __future__ import annotations

import pytest

from tapaz_sdk import InvalidRequestError, PropertyKind, gid, legacy_id


def test_global_ids():
    assert gid("Category", "635") == "Z2lkOi8vdGFwL0NhdGVnb3J5LzYzNQ"
    assert gid("Category", "Z2lkOi8vdGFwL0NhdGVnb3J5LzYzNQ") == "Z2lkOi8vdGFwL0NhdGVnb3J5LzYzNQ"
    assert legacy_id(gid("Ad", 5001)) == "5001" and legacy_id("5001") == "5001" and legacy_id(None) is None


def test_category_tree(guest, site):
    tree = guest.catalog.categories()
    assert tree[0].id == "606" and not tree[0].leaf and tree[0].children[0].id == "635"
    assert [c.id for c in tree[0].walk()] == ["606", "635"]
    assert "cookie" not in site.requests[0].headers
    assert site.requests[0].headers["origin"] == "https://tap.az"


def test_category_properties(guest):
    category = guest.catalog.category(635)
    assert category.photo_required and category.price_required and not category.title_required
    kind = category.find_property("740")
    assert kind is not None and kind.kind == PropertyKind.COLLECTION and kind.options[1].enables == ("994",)
    rent = category.find_property("994")
    assert rent is not None and rent.depends_on == "740"
    area = category.find_property("737")
    assert area is not None and area.kind == PropertyKind.RANGE and area.min == 1.0 and area.unit == "m2"
    assert category.find_property("812").kind == PropertyKind.STRING
    assert category.find_property("900").kind == PropertyKind.BOOLEAN


def test_unknown_category(guest):
    with pytest.raises(InvalidRequestError):
        guest.catalog.category("1")
    with pytest.raises(InvalidRequestError):
        guest.catalog.category("../x")


def test_options_regions_contact_types(guest, site):
    options = guest.catalog.property_options("3724")
    assert [(o.id, o.name, o.property_id) for o in options] == [("38046", "Monthly", "994")]
    assert site.last("PropertyOptions")["variables"] == {"p": "3724"}
    region = guest.catalog.regions()[0]
    assert (region.id, region.name, region.default) == ("420", "Baku", True)
    kinds = guest.catalog.contact_types()
    assert kinds[0].id == "CALLS_AND_MESSAGES" and kinds[0].default
