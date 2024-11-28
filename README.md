# Kubex

Kubex is a Kubernetes client library for Python inspired by kube.rs. It is built on top of [Pydantic](https://github.com/pydantic/pydantic) and is async-runtime agnostic.

> *ATTENTION:* Kubex is currently under active development, and backward compatibility may be broken in future releases.

# Completed Features:

* Basic API interface that allows interaction with almost any Kubernetes resources and their methods.
* In-cluster client authorization with token refreshing.
* Basic support for kubeconfig files.
* `httpx` and `aiohttp` as an underlying http-client support
* `asyncio` and `trio` async runtime support (only `httpx` client is supported for `trio`)

# Planned Features:

* [ ] Support for OIDC and other authentication extensions.
* [ ] Fine-tuning of timeouts.
* [ ] Comprehensive library of Kubernetes models.
* [ ] Dynamic API object creation to exclude unsupported methods for resources (requires research for mypy compatibility).
* [ ] Potential synchronous version of the client.
* [ ] Additional tests and examples.
* [ ] JsonPatch models.
* [ ] Enhanced support for subresources (status, ephemeral containers).
* [ ] Support for Pod.attach.
