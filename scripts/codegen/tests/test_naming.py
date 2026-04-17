from __future__ import annotations

import pytest

from scripts.codegen.naming import (
    camel_to_snake,
    class_name_for_enum,
    py_field_name,
    screaming_snake,
)


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("internalIP", "internal_ip"),
        ("someNiceAPI", "some_nice_api"),
        ("podIPs", "pod_ips"),
        ("HTTPSProxy", "https_proxy"),
        ("apiVersion", "api_version"),
        ("kind", "kind"),
        ("x509", "x509"),
        ("IPs", "ips"),
    ],
)
def test_camel_to_snake(input_: str, expected: str) -> None:
    assert camel_to_snake(input_) == expected


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("continue", "continue_"),
        ("type", "type_"),
        ("class", "class_"),
        ("namespace", "namespace"),
        ("podIPs", "pod_ips"),
    ],
)
def test_py_field_name(input_: str, expected: str) -> None:
    assert py_field_name(input_) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Pending", "PENDING"),
        ("ReplicaFailure", "REPLICA_FAILURE"),
        ("Available", "AVAILABLE"),
        ("100Gi", "_100_GI"),
        ("a/b", "A_B"),
    ],
)
def test_screaming_snake(value: str, expected: str) -> None:
    assert screaming_snake(value) == expected


def test_class_name_for_enum() -> None:
    assert (
        class_name_for_enum("ContainerStateWaiting", "reason")
        == "ContainerStateWaitingReason"
    )
    assert class_name_for_enum("Pod", "phase") == "PodPhase"
