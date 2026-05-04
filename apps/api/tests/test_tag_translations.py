"""Sanity tests for the PL → EN tag map used by the migration script."""

from scripts.tag_translations import PL_EN


def test_pl_en_keys_are_lowercase():
    for key in PL_EN:
        assert key == key.lower(), f"key {key!r} not lowercase"


def test_pl_en_values_are_lowercase_ascii_slugs():
    for value in PL_EN.values():
        assert value == value.lower(), f"value {value!r} not lowercase"
        # Tag slugs are ASCII (ż / ł / etc. only allowed on the PL key side)
        assert value.isascii(), f"value {value!r} not ASCII"


def test_no_pl_key_overlaps_an_en_value_for_a_different_concept():
    """If 'foo' is a PL key and also appears as an EN value for some OTHER PL key,
    the migration would translate 'foo' both into itself AND into the other concept,
    creating ambiguity. Detect this collision early."""
    en_values = set(PL_EN.values())
    for pl_key, en_value in PL_EN.items():
        if pl_key in en_values and pl_key != en_value:
            # 'pl_key' is also someone else's EN target — find which:
            collisions = [k for k, v in PL_EN.items() if v == pl_key]
            raise AssertionError(
                f"PL key {pl_key!r} also appears as an EN value for {collisions}; this is ambiguous"
            )


def test_known_animal_pairs_present():
    """Sanity: the most common pairs must be in the map."""
    expected = {
        "smok": "dragon",
        "krab": "crab",
        "jajko": "egg",
        "kot": "cat",
        "królik": "rabbit",
        "słoń": "elephant",
    }
    for k, v in expected.items():
        assert PL_EN.get(k) == v, f"expected {k!r} → {v!r}, got {PL_EN.get(k)!r}"


def test_no_self_mapping():
    """A key 'foo' mapping to value 'foo' is pointless (would tag both PL and EN as 'foo').
    The map should only contain genuine PL→EN translations."""
    self_maps = {k: v for k, v in PL_EN.items() if k == v}
    # Exception: 'test' is the same in both languages and is intentionally listed
    self_maps.pop("test", None)
    assert self_maps == {}, f"unexpected self-mapping: {self_maps}"
