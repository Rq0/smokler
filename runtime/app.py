from datetime import datetime
from uuid import uuid4

from boto3.dynamodb.conditions import Key

from chalicelib.dependency.cognito import IUsername
from chalicelib.dependency.injection import inject
from chalicelib.dependency.register import DependencyRegister
from chalicelib.user import User

dependency_register = DependencyRegister()

app = dependency_register.app
authorizer = dependency_register.authorizer
user_table = dependency_register.user_table


@app.route('/comment', methods=['POST'], authorizer=authorizer)
@inject(username=IUsername)
def create_comment(username: IUsername):
    body = app.current_request.json_body
    user_table.put_item(Item={
        'PK': f'User#{username}',
        'SK': f'Comment#{uuid4()}',
        'text': body['text']
    })
    return {'success': True}


@app.route('/comment', methods=['GET'], authorizer=authorizer)
@inject(username=IUsername)
def get_comments(username: IUsername):
    filter_expression = \
        Key('PK').eq(f'User#{username}') & \
        Key('SK').begins_with('Comment')
    comments_db = user_table.query(
        KeyConditionExpression=filter_expression
    )['Items']
    return comments_db


@app.route('/event', methods=['POST'], authorizer=authorizer)
@inject(username=IUsername)
def create_event(username: IUsername):
    body = app.current_request.json_body
    if 'type' not in body:
        return {'success': False, 'error': 'attr "type" not provided in request body'}
    user_table.put_item(Item={
        'PK': f'User#{username}',
        'SK': f'Event#{uuid4()}',
        'type': body['type'],
        'date': datetime.now()
    })
    return {'success': True}


@app.route('/event', methods=['GET'], authorizer=authorizer)
@inject(username=IUsername)
def get_events(username: IUsername):
    filter_expression = \
        Key('PK').eq(f'User#{username}') & \
        Key('SK').begins_with('Event#')
    return user_table.query(
        KeyConditionExpression=filter_expression
    )['Items']


@app.route('/me', methods=['GET'], authorizer=authorizer)
@inject(username=IUsername)
def get_me(username: IUsername):
    filter_expression = \
        Key('PK').eq(f'User#{username}') & \
        Key('SK').eq('Profile')
    try:
        database_user = user_table.query(
            KeyConditionExpression=filter_expression
        )['Items'][0]
    except IndexError:
        return {'success': False, 'error': "User doesn't exists"}
    user = User.deserialize(database_user)
    return user.json


@app.route('/settings', methods=['POST'], authorizer=authorizer)
@inject(username=IUsername)
def update_notification_settings(username: IUsername):
    body = app.current_request.json_body
    user_table.update_item(Item={
        'PK': f'User#{username}',
        'SK': f'Settings#{uuid4()}',
        'type': body['type'],
        'date': datetime.now()
    })
