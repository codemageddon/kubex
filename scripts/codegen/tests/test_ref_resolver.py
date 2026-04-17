from __future__ import annotations

import pytest

from scripts.codegen.ref_resolver import module_for_definition, resolve


@pytest.mark.parametrize(
    ("definition", "expected_module", "expected_cls"),
    [
        (
            "io.k8s.api.core.v1.Pod",
            "kubex.k8s.v1_30.core.v1.pod",
            "Pod",
        ),
        (
            "io.k8s.api.core.v1.PersistentVolumeClaim",
            "kubex.k8s.v1_30.core.v1.persistent_volume_claim",
            "PersistentVolumeClaim",
        ),
        (
            "io.k8s.api.apps.v1.Deployment",
            "kubex.k8s.v1_30.apps.v1.deployment",
            "Deployment",
        ),
        (
            "io.k8s.api.networking.v1.Ingress",
            "kubex.k8s.v1_30.networking.v1.ingress",
            "Ingress",
        ),
    ],
)
def test_module_for_definition_api(
    definition: str, expected_module: str, expected_cls: str
) -> None:
    module, cls = module_for_definition(definition, k8s_version_tag="v1_30")
    assert module == expected_module
    assert cls == expected_cls


@pytest.mark.parametrize(
    ("definition", "expected_module", "expected_cls"),
    [
        (
            "io.k8s.apiextensions-apiserver.pkg.apis.apiextensions.v1.CustomResourceDefinition",
            "kubex.k8s.v1_30.apiextensions_k8s_io.v1.custom_resource_definition",
            "CustomResourceDefinition",
        ),
        (
            "io.k8s.kube-aggregator.pkg.apis.apiregistration.v1.APIService",
            "kubex.k8s.v1_30.apiregistration.v1.api_service",
            "APIService",
        ),
        (
            "io.k8s.apimachinery.pkg.apis.meta.v1.Status",
            "kubex.k8s.v1_30.meta.v1.status",
            "Status",
        ),
    ],
)
def test_module_for_definition_non_api(
    definition: str, expected_module: str, expected_cls: str
) -> None:
    module, cls = module_for_definition(definition, k8s_version_tag="v1_30")
    assert module == expected_module
    assert cls == expected_cls


def test_resolve_override_unchanged() -> None:
    r = resolve(
        "io.k8s.apimachinery.pkg.apis.meta.v1.ObjectMeta", k8s_version_tag="v1_30"
    )
    assert r.is_override is True
    assert r.module == "kubex_core.models.metadata"
    assert r.class_name == "ObjectMetadata"


def test_resolve_alias_unchanged() -> None:
    r = resolve(
        "io.k8s.apimachinery.pkg.util.intstr.IntOrString", k8s_version_tag="v1_30"
    )
    assert r.is_alias is True
    assert r.alias_expression == "int | str"
