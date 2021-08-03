import binascii
import uuid

import sqlalchemy.types as types
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


# https://stackoverflow.com/questions/28143557/sqlalchemy-convert-column-value-back-and-forth-between-internal-and-database-fo

class PublicKeyModel(types.TypeDecorator):
    impl = types.BINARY

    cache_ok = True

    def process_literal_param(self, value, dialect):
        if value is None:
            return b"0"
        if isinstance(value, str):
            # For simplicity when mining, the public key is allowed to be a string so the miner simply has to put
            # the ascii encoding of the key instead of the actual byte version occurs under POST /api/mine
            value = serialization.load_der_public_key(binascii.unhexlify(value))
        return value.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        if value == b"0":
            return None
        return serialization.load_der_public_key(value)


class UUIDModel(types.TypeDecorator):
    impl = types.TEXT

    cache_ok = True

    def process_literal_param(self, value, dialect):
        return str(value) if value is not None else ""

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return uuid.UUID(value) if value != "" else ""
