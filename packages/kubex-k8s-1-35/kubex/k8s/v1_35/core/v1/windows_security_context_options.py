from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class WindowsSecurityContextOptions(BaseK8sModel):
    """WindowsSecurityContextOptions contain Windows-specific options and credentials."""

    gmsa_credential_spec: str | None = Field(
        default=None,
        alias="gmsaCredentialSpec",
        description="GMSACredentialSpec is where the GMSA admission webhook (https://github.com/kubernetes-sigs/windows-gmsa) inlines the contents of the GMSA credential spec named by the GMSACredentialSpecName field.",
    )
    gmsa_credential_spec_name: str | None = Field(
        default=None,
        alias="gmsaCredentialSpecName",
        description="GMSACredentialSpecName is the name of the GMSA credential spec to use.",
    )
    host_process: bool | None = Field(
        default=None,
        alias="hostProcess",
        description="HostProcess determines if a container should be run as a 'Host Process' container. All of a Pod's containers must have the same effective HostProcess value (it is not allowed to have a mix of HostProcess containers and non-HostProcess containers). In addition, if HostProcess is true then HostNetwork must also be set to true.",
    )
    run_as_user_name: str | None = Field(
        default=None,
        alias="runAsUserName",
        description="The UserName in Windows to run the entrypoint of the container process. Defaults to the user specified in image metadata if unspecified. May also be set in PodSecurityContext. If set in both SecurityContext and PodSecurityContext, the value specified in SecurityContext takes precedence.",
    )
