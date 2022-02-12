# pylint: disable="redefined-outer-name,missing-function-docstring,unused-import"
from os import remove
from tempfile import NamedTemporaryFile

import pytest

from gpg.gpg import GPGSigning


@pytest.fixture
def test_altered_file():
    """Create altered asset file to fail gpg verification"""
    altered_asset = NamedTemporaryFile(delete=False)
    with open(altered_asset.name, "w", encoding="utf-8") as outfile:
        outfile.write("test signatur")
    return altered_asset.name


@pytest.fixture
def test_file():
    """Create test asset file"""
    asset = NamedTemporaryFile(delete=False)
    with open(asset.name, "w", encoding="utf-8") as outfile:
        outfile.write("test signature")
    return asset.name


@pytest.fixture
def sig_file():
    """Create test asset signature file"""
    signature = """-----BEGIN PGP SIGNATURE-----

iQIzBAABCAAdFiEEv63QGy0SoKtjxi9GA874CySxgXcFAmIH/D8ACgkQA874CySx
gXfXeRAAqtuc+qBB1fhpULYTvlDVs7NxbX0Xs1IZ07Sj5qOruoyFEkMJuQTbTXE6
ubiwTTP+L5tcG9rnq3uV92xIIfSeg5L2fB/Z1pl7Fl5pn6T7krKbGJ1eIQYrhH+g
GAXp+XYwDsbgc30GZ4SJYxWNWGVqZE8JVBXS0huzr5+wI2ftYiomOxQ5NandI3Ia
OMJZ0jFkYPu2r4ND6aukeLo6FVGjyjkhgT4HG1zfeyKpkdxTzczgw7rzVTpc8KY7
rRP3z+pHqbTV0DQ932i9wpaubqDzbhyvKA/3qZlXYKRHHLWz3IIiPKgLL0/U/LQr
/Vih481Ofq9Vh600d+Ib0mXvXYJIg2g2WMzohbJB8JJPidmqba5vRZUomhEfVJ9H
BOoxatWxAp8i4KLbG3tWgqDoAQ18dc969VjSpicd/hCqdPR+I7PE4RbPT32l15Nx
FfDIWVjVpoBiUqwP6EyUPejtAL8wmntkt3KXinavCvwhn7uICqkfckn3y3kKCwCW
Ie/1qg3bQb0jgmQFzf567xm85eWm331i/NFYlBmZY5xgP2fwXXND/bgOTxmkAd4i
a2AIPcpeZv+81iPRPE/xUY2YMgsM8ZeO4z5/rFHCVXJm0fkHGfzh+PNJiA4yAVJw
2IlEx0zx2avPkr++CzY56ueSEsju31AfVjkYradO9cQgQSJcBHc=
=7oNE
-----END PGP SIGNATURE-----
"""
    asset_sig = NamedTemporaryFile(delete=False)
    with open(asset_sig.name, "w", encoding="utf-8") as outfile:
        outfile.write(signature)
    return asset_sig.name


@pytest.fixture
def sig_file_wrong_key():
    """Create test asset signature file - wrong pgp key"""
    signature = """-----BEGIN PGP SIGNATURE-----

iQIzBAABCAAdFiEEIO1YPKcoinM5ZwoiSRkudDqKh0sFAmIICuAACgkQSRkudDqK
h0uD4g/+PivPyEAXW3bbnqAyWG7XePaApmodGM71hE3j+ledH3qHjrAE8JSqyOM8
XH6PPHtejijVzffIguV2Y1hEyYvHMOSjRrUdFeIRZaR90s/YJJKGu4xJeyvGfSVA
5gzzy1iVKYxzxi6I4raCAoelir6HIK0WV4hBtwppQidWlWLZ0Q/3yIF3F4x3y59S
kzvT3gRR4vKuj33sXY6IJVVIsoeP+g7oFuN/yM+xrEAUQb4tufyJd3vIhbCxM7rU
Cywbqk3l+zSvRfZJ83LYVQIILWLs4bGmBi3qSrnPUUwT0sx9LsNbOsUIzaQf+/sE
FTI/Eypkcp51GBqsZIHxzbWXTEmDRH4IkBaEf/em+7GTFbS2S92ynw4fWbRpuFXq
yzkrYDb/tQyxQi+JEmJHiLGs8XPn1MK9fItpnP1PY2by+QRHNX1cj2HX86Gg+Y5W
7WGNn0Pw8ibVYnr4bENGQQCTo+i7Cozluw/DB3pVADFt7wHftIJFgz2JgOfkus1x
5yqgQUx9npixpNf5c2THCf4PYjw1WSVmU8NaHNxZFe70lleOdsSy2lCc6qk3WvFi
XwWRuzTnoSqY0g2eX4Leje31BnF0llRZ9cQ6HwmBehJZCvz5e0M2jwDZpEO4Xdxp
it42eeYN11osRw/quVQVUgZnunX2xZDrGKAl3p0s8UBi/VSTsr8=
=78Bb
-----END PGP SIGNATURE-----
"""
    asset_sig = NamedTemporaryFile(delete=False)
    with open(asset_sig.name, "w", encoding="utf-8") as outfile:
        outfile.write(signature)
    return asset_sig.name


def test_gpg_verify_valid(test_file, sig_file):
    """Test signature for the signing key found in this repo"""
    verify = GPGSigning().verify_signature(sig_file, test_file)
    remove(test_file)
    remove(sig_file)
    assert verify


def test_gpg_verify_invalid_signature(test_altered_file, sig_file):
    """Negative test case for test signature for the signing key found in this repo"""
    verify = GPGSigning().verify_signature(sig_file, test_altered_file)
    remove(test_altered_file)
    remove(sig_file)
    assert not verify


def test_gpg_verify_valid_signature_wrong_gpg_key(test_file, sig_file_wrong_key):
    """Negative test case for test signature for the signing key found in this repo"""
    verify = GPGSigning().verify_signature(sig_file_wrong_key, test_file)
    remove(test_file)
    remove(sig_file_wrong_key)
    assert not verify
