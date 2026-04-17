"""Kubernetes OpenAPI -> Pydantic v2 code generator for Kubex.

Emits one distribution package per Kubernetes version (`kubex-k8s-1.30`, etc.)
containing Pydantic models that plug into the `kubex_core.models.*` base types.

See /home/user/kubex/scripts/codegen/__main__.py for the CLI entrypoint.
"""
