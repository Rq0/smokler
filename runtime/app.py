import os
from uuid import uuid4

from boto3 import resource
from boto3.dynamodb.conditions import Key
from chalice import Chalice, CognitoUserPoolAuthorizer

authorizer = CognitoUserPoolAuthorizer(
    'CognitoAuthorizer',
    provider_arns=[os.environ.get('COGNITO_USER_POOL_ARN', '')],
    header='Authorization', scopes=None
)

app = Chalice(app_name=os.environ.get('APP_NAME', ''))
dynamodb = resource('dynamodb')
dynamodb_table = dynamodb.Table(os.environ.get('USER_TABLE_NAME', ''))


@app.route('/comment', methods=['POST'], authorizer=authorizer)
def create_comment():
    body = app.current_request.json_body
    auth_context = app.current_request.context.get('authorizer', {})
    user = auth_context.get('claims', {}).get('cognito:username')
    dynamodb_table.put_item(Item={
        'PK': f'User#{user}',
        'SK': f'Comment#{uuid4()}',
        'text': body['text']
    })
    return {'success': True}


@app.route('/comment', methods=['GET'], authorizer=authorizer)
def get_comments():
    auth_context = app.current_request.context.get('authorizer', {})
    user = auth_context.get('claims', {}).get('cognito:username')
    filter_expression = \
        Key('PK').eq(f'User#{user}') & \
        Key('SK').begins_with('Comment')
    comments_db = dynamodb_table.query(
        KeyConditionExpression=filter_expression
    )['Items']
    return comments_db
