import uuid
from abc import ABC

import sqlalchemy.types as types
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey


# https://stackoverflow.com/questions/28143557/sqlalchemy-convert-column-value-back-and-forth-between-internal-and-database-fo

class PublicKeyModel(types.TypeDecorator):
    impl = types.BINARY

    def process_literal_param(self, value, dialect):
        return value.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return serialization.load_der_public_key(value)


class UUIDModel(types.TypeDecorator):
    impl = types.TEXT

    def process_literal_param(self, value, dialect):
        return str(value)

    process_bind_param = process_literal_param

    def process_result_value(self, value, dialect):
        return uuid.UUID(value)
