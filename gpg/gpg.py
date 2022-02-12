from shutil import rmtree
from tempfile import mkdtemp

import gnupg


class GPGSigning:
    """Class to gpg verify artifacts"""

    __instance = None
    _gpghome = None

    def __new__(cls):
        if GPGSigning.__instance is None:
            GPGSigning.__instance = object.__new__(cls)
            cls._gpghome = mkdtemp(prefix="gpg")
            cls._gpg = gnupg.GPG(gnupghome=cls._gpghome)
            with open("gpg_signing_key.gpg", "rb") as stream:
                datakey = stream.read()
            cls._gpg.import_keys(datakey)
        return GPGSigning.__instance

    @classmethod
    def __del__(cls):
        rmtree(cls._gpghome)

    def verify_signature(self, signature: str, artifact: str) -> bool:
        """Verify a GPG signature

        Args:
            signature (str): Detached signature
            artifact (str): Artifact (file) to verify

        Returns:
            bool: Is the artifact signature valid
        """
        with open(signature, "rb") as stream:
            verified = self._gpg.verify_file(stream, artifact)
        return verified.fingerprint == self._gpg.list_keys()[0]["fingerprint"]
