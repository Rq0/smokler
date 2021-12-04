import abc


class IUsername(abc.ABC):
    @abc.abstractmethod
    def __str__(self):
        pass


class CognitoUsername(IUsername):
    def __init__(self, app):
        self.__app = app

    def __str__(self):
        auth_context = self.__app.current_request.context.get('authorizer', {})
        username = auth_context.get('claims', {}).get('cognito:username')
        return username


class FakeUsername(IUsername):
    def __str__(self):
        return 'FakeUser3301'
