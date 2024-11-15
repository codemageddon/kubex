# Kubex

Kubex is a Kubernetes client library for Python inspired by kube.rs. It is built on top of [Pydantic](https://github.com/pydantic/pydantic) and is async-runtime agnostic.

> *ATTENTION:* Kubex is currently under active development, and backward compatibility may be broken in future releases.

# Completed Features:

* Basic API interface that allows interaction with almost any Kubernetes resources and their methods.
* In-cluster client authorization with token refreshing.
* Basic support for kubeconfig files.

# Planned Features:

* [ ] Support for OIDC and other authentication extensions.
* [ ] Integration with aiohttp as an internal HTTP client.
* [ ] Fine-tuning of timeouts.
* [ ] Comprehensive library of Kubernetes models.
* [ ] Dynamic API object creation to exclude unsupported methods for resources (requires research for mypy compatibility).
* [ ] Potential synchronous version of the client.
* [ ] Additional tests and examples.
* [ ] JsonPatch models.
* [ ] Allow `namespace` to be a method parameter instead of an API instance-scoped parameter.
* [ ] Enhanced support for subresources (status, ephemeral containers).
* [ ] Support for Pod.attach.