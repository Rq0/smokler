import os

from boto3 import resource

USER_TABLE_NAME = os.environ.get('USER_TABLE_NAME', '')
dynamodb = resource('dynamodb')
user_table = dynamodb.Table(USER_TABLE_NAME)


def sign_up_trigger(event, context):
    user_table.put_item(
        Item={
            'PK': f'User#{event["userName"]}',
            'SK': 'Profile',
            'locale': 'ru',
            'theme': 0,
            'selected_course': 0,
        }
    )
    return event
