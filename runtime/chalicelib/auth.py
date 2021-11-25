import base64
import datetime
import hashlib
import hmac
import os
from dataclasses import dataclass
from uuid import uuid4

import boto3
import jwt
from chalice import UnauthorizedError

_AUTH_KEY = b'Xg1yuC2JRUOzNlXxHtxyzA=='
_SSM_AUTH_KEY_NAME = '/smokler/auth-key'


@dataclass
class User:
    username: str
    hashed: bytes = b''
    salt: bytes = os.urandom(32)
    rounds: int = 100000

    algorithms: str = 'HS256'

    def encode_password(self, password, salt=None):
        if salt:
            self.salt = salt
        self.hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, self.rounds)
        self.salt = salt

    def get_jwt_token(self, password, record):
        return JwtAuth.get_jwt_token(
            username=self.username,
            password=password,
            record=record,
        )

    @property
    def dynamodb_profile_key(self):
        return {
            'PK': f'User#{self.username}',
            'SK': f'Profile#{self.username}',
        }


@dataclass
class JwtAuth:
    @classmethod
    def get_jwt_token(cls, username, password, record):
        actual = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            record['salt'].value,
            record['rounds']
        )
        if not hmac.compare_digest(actual, record['hashed'].value):
            raise UnauthorizedError('Invalid password')

        now = datetime.datetime.utcnow()
        return jwt.encode(
            payload={
                'sub': username,
                'iat': now,
                'nbf': now,
                'jti': str(uuid4()),
                # NOTE: We can also add 'exp' if we want tokens to expire.
            },
            key=cls.__get_auth_key(),
            algorithm=User.algorithms
        )

    @classmethod
    def decode_jwt_token(cls, token):
        return jwt.decode(token, cls.__get_auth_key(), algorithms=[User.algorithms])

    @staticmethod
    def __get_auth_key():
        global _AUTH_KEY
        if _AUTH_KEY is None:
            base64_key = boto3.client('ssm').get_parameter(
                Name=_SSM_AUTH_KEY_NAME,
                WithDecryption=True
            )['Parameter']['Value']
            _AUTH_KEY = base64.b64decode(base64_key)
        return _AUTH_KEY
