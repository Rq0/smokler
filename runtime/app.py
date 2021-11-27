import os
from uuid import uuid4

from boto3 import resource
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from chalice import Chalice, AuthResponse, UnauthorizedError

from chalicelib.auth import User, JwtAuth

app = Chalice(app_name='smokler')
dynamodb = resource('dynamodb')
dynamodb_table = dynamodb.Table(os.environ.get('USER_TABLE_NAME', ''))


@app.authorizer()
def authorizer(auth_request):
    decoded = JwtAuth.decode_jwt_token(auth_request.token)
    return AuthResponse(routes=['*'], principal_id=decoded['sub'])


@app.route('/register', methods=['POST'])
def register():
    request = app.current_request.json_body
    user = User(username=request.pop("username"))
    user.encode_password(request.pop("password"))
    try:
        dynamodb_table.put_item(
            Item={

                'username': user.username,
                'hashed': user.hashed,
                'salt': user.salt,
                'rounds': user.rounds,
                **user.dynamodb_profile_key,
                **request,  # save request body without password
            },
            ConditionExpression='attribute_not_exists(PK) AND attribute_not_exists(SK)'
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'error': True, 'text': 'User with this username already exists'}
        raise
    return {}


@app.route('/login', methods=['POST'])
def login():
    body = app.current_request.json_body
    user = User(username=body["username"])
    user_db = dynamodb_table.get_item(Key={
        **user.dynamodb_profile_key
    }).get('Item')
    if not user_db:
        raise UnauthorizedError('Invalid username or password')
    jwt_token = user.get_jwt_token(body['password'], user_db)
    return {'token': jwt_token}


@app.route('/comment', methods=['POST'], authorizer=authorizer)
def create_comment():
    body = app.current_request.json_body
    comment = dynamodb_table.put_item(Item={
        'PK': f'User#{app.current_request.context["authorizer"]["principalId"]}',
        'SK': f'Comment#{uuid4()}',
        'text': body['text']
    })
    return comment


@app.route('/comment', methods=['GET'], authorizer=authorizer)
def get_comments():
    filter_expression = \
        Key('PK').eq(f'User#{app.current_request.context["authorizer"]["principalId"]}') & \
        Key('SK').begins_with('Comment')
    comments_db = dynamodb_table.query(
        KeyConditionExpression=filter_expression
    )['Items']
    return comments_db


@app.route('/users/{username}', methods=['GET'], authorizer=authorizer)
def get_user(username: str):
    user_db = dynamodb_table.get_item(
        Key={
            **User(username=username).dynamodb_profile_key
        }
    )['Item']
    del user_db['PK']
    del user_db['SK']
    return user_db
