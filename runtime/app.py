import json
from datetime import datetime
from uuid import uuid4

from boto3.dynamodb.conditions import Key

from chalicelib.dependency.cognito import IUsername
from chalicelib.dependency.injection import inject
from chalicelib.dependency.register import DependencyRegister
from chalicelib.user import User, NotificationSettings, Theme, Course

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


@app.route('/user', methods=['GET'], authorizer=authorizer)
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
    return json.dumps(user.json)


@app.route('/user', methods=['POST'], authorizer=authorizer)
@inject(username=IUsername)
def update_basic_settings(username: IUsername):
    body = app.current_request.json_body
    user_table.update_item(
        Key={
            'PK': f'User#{username}',
            'SK': 'Profile',
        },
        UpdateExpression="SET username = :username, avatar = :avatar, locale = :locale, theme = :theme,"
                         " selected_course = :selected_course",
        ExpressionAttributeValues={
            ':username': body['username'],
            ':avatar': body['avatar'],
            ':locale': body['locale'],
            ':theme': Theme[body['theme']].value,
            ':selected_course': Course[body['selected_course']].value,
        },
    )
    return {'success': True}


@app.route('/notification_settings', methods=['POST'], authorizer=authorizer)
@inject(username=IUsername)
def update_notification_settings(username: IUsername):
    body = app.current_request.json_body
    notification_settings = NotificationSettings(
        **body['notification_settings']
    )
    user_table.update_item(
        Key={
            'PK': f'User#{username}',
            'SK': 'Profile',
        },
        UpdateExpression=f"SET #field = :field_value",
        ExpressionAttributeNames={
            '#field': 'notification_settings',
        },
        ExpressionAttributeValues={
            ':field_value': notification_settings.__dict__,
        },
    )
    return {'success': True}


@app.route('/upload/', methods=['PUT'], content_types=['application/octet-stream'], authorizer=authorizer)
def upload_avatar():
    with open(f'/tmp/{"filename"}', 'wb') as tmp_file:
        tmp_file.write(app.current_request.raw_body)

    dependency_register.s3.upload_file(f'/tmp/{"filename"}', dependency_register.media_bucket_name, "filename.jpg")
    return {'success': True}
