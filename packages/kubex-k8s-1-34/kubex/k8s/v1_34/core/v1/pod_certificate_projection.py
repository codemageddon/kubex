from kubex_core.models.base import BaseK8sModel
from pydantic import Field


class PodCertificateProjection(BaseK8sModel):
    """PodCertificateProjection provides a private key and X.509 certificate in the pod filesystem."""

    certificate_chain_path: str | None = Field(
        default=None,
        alias="certificateChainPath",
        description="Write the certificate chain at this path in the projected volume. Most applications should use credentialBundlePath. When using keyPath and certificateChainPath, your application needs to check that the key and leaf certificate are consistent, because it is possible to read the files mid-rotation.",
    )
    credential_bundle_path: str | None = Field(
        default=None,
        alias="credentialBundlePath",
        description="Write the credential bundle at this path in the projected volume. The credential bundle is a single file that contains multiple PEM blocks. The first PEM block is a PRIVATE KEY block, containing a PKCS#8 private key. The remaining blocks are CERTIFICATE blocks, containing the issued certificate chain from the signer (leaf and any intermediates). Using credentialBundlePath lets your Pod's application code make a single atomic read that retrieves a consistent key and certificate chain. If you project them to separate files, your application code will need to additionally check that the leaf certificate was issued to the key.",
    )
    key_path: str | None = Field(
        default=None,
        alias="keyPath",
        description="Write the key at this path in the projected volume. Most applications should use credentialBundlePath. When using keyPath and certificateChainPath, your application needs to check that the key and leaf certificate are consistent, because it is possible to read the files mid-rotation.",
    )
    key_type: str = Field(
        ...,
        alias="keyType",
        description='The type of keypair Kubelet will generate for the pod. Valid values are "RSA3072", "RSA4096", "ECDSAP256", "ECDSAP384", "ECDSAP521", and "ED25519".',
    )
    max_expiration_seconds: int | None = Field(
        default=None,
        alias="maxExpirationSeconds",
        description="maxExpirationSeconds is the maximum lifetime permitted for the certificate. Kubelet copies this value verbatim into the PodCertificateRequests it generates for this projection. If omitted, kube-apiserver will set it to 86400(24 hours). kube-apiserver will reject values shorter than 3600 (1 hour). The maximum allowable value is 7862400 (91 days). The signer implementation is then free to issue a certificate with any lifetime *shorter* than MaxExpirationSeconds, but no shorter than 3600 seconds (1 hour). This constraint is enforced by kube-apiserver. `kubernetes.io` signers will never issue certificates with a lifetime longer than 24 hours.",
    )
    signer_name: str = Field(
        ...,
        alias="signerName",
        description="Kubelet's generated CSRs will be addressed to this signer.",
    )
