import os

from boto3 import resource
from chalice import Chalice, CognitoUserPoolAuthorizer

from chalicelib.dependency.cognito import CognitoUsername, IUsername, FakeUsername
from chalicelib.dependency.injection import _Dependencies

APP_NAME = os.environ.get('APP_NAME', '')
COGNITO_USER_POOL_ARN = os.environ.get('COGNITO_USER_POOL_ARN', '')

_dependencies = _Dependencies()


class DependencyRegister:
    """Place to register app dependencies"""
    _instance = None
    __container = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.__add_app()
        self.__add_database()
        self.__add_authorizer()

    def __getattr__(self, dependency_name):
        return self.__container.get(dependency_name)

    def __add_app(self):
        self.__app = Chalice(app_name=APP_NAME)
        self.__container['app'] = self.__app

    def __add_database(self):
        dynamodb = resource('dynamodb')
        self.__container['user_table'] = dynamodb.Table(os.environ.get('USER_TABLE_NAME', ''))

    def __add_authorizer(self):
        if COGNITO_USER_POOL_ARN:
            _dependencies.register(CognitoUsername(app=self.__app))
            self.__container['authorizer'] = CognitoUserPoolAuthorizer(
                'CognitoAuthorizer',
                provider_arns=[COGNITO_USER_POOL_ARN],
                header='Authorization', scopes=None
            )
        else:
            _dependencies.register(FakeUsername())
            self.__container['authorizer'] = self.__app.authorizer()
