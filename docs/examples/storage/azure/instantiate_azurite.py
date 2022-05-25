from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

cls = get_driver(Provider.AZURE_BLOBS)

driver = cls(
    key="devstoreaccount1",
    secret="Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6"
    "IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
    host="localhost",
    port=10000,
    secure=False,
)
