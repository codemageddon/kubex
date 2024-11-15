# Kubex

Kubex is a Kubernetes client library for Python inspired by kube.rs
Kubex is built on top of [Pydantic](https://github.com/pydantic/pydantic) and async-runtime agnostic

> *ATTENTION:* Kubex is in the active development stage and backward compatibility may be broken in
> future releases.

# Done:

* Basic Api interface that allows to work with almost any Kuebrnetes resources and theirs methods
* Incluster client authorization with token refreashing
* Basic support for kubeconfig file.

# TODOs

* [ ] Support OIDC and other auth extensions
* [ ] Support aiohttp as an inner HTTTP-client
* [ ] Tune timeouts
* [ ] Kubernetes models library-set
* [ ] Dynamic Api object creation to exclude methods that are not supported by the resource (requires some research for mypy compatibility)
* [ ] ?Synchtronous version of the client?
* [ ] More tests and examples
* [ ] JsonPatch models?
* [ ] Put `namesapace` as a method parameter instead of Api-instance-scoped parameter
* [ ] More subresources support (status, ephimeral containers)
* [ ] Pod.attach support