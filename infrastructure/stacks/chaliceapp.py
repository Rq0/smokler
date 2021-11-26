import os

from aws_cdk import (
    aws_dynamodb as dynamodb,
    core as cdk,
    aws_cognito as cognito
)
from chalice.cdk import Chalice

RUNTIME_SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), os.pardir, 'runtime')


class ChaliceApp(cdk.Stack):
    chalice: Chalice
    dynamodb_table: dynamodb.Table
    user_pool: cognito.UserPool
    stage = 'api'  # TODO: add ref to configs

    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self._create_ddb_table()
        self._add_cognito()
        self.chalice = Chalice(
            self, 'ChaliceApp', source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                'environment_variables': {
                    'USER_TABLE_NAME': self.dynamodb_table.table_name
                }
            }
        )
        self.dynamodb_table.grant_read_write_data(
            self.chalice.get_role('DefaultRole')
        )

    def _create_ddb_table(self):
        self.dynamodb_table = dynamodb.Table(
            self, 'UserTable',
            partition_key=dynamodb.Attribute(
                name='PK', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name='SK', type=dynamodb.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY)
        cdk.CfnOutput(
            self, 'UserTableName', value=self.dynamodb_table.table_name)

    def _add_cognito(self):
        """
        Sets up the cognito infrastructure with the user pool, custom domain
        and app client for use by the S3, lambda.
        """
        # Create the user pool that holds our users
        self.user_pool = cognito.UserPool(
            self,
            "user_pool",
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            self_sign_up_enabled=True,
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(mutable=True, required=True),
                given_name=cognito.StandardAttribute(mutable=True, required=True),
                family_name=cognito.StandardAttribute(mutable=True, required=True)
            )
        )
        self.identity_pool = cognito.CfnIdentityPool(
            self,
            id="identity_pool",
            identity_pool_name=f"smokler-{self.stage}",
            allow_unauthenticated_identities=True,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool.user_pool_id,
                    provider_name=f"cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}",
                )
            ],
        )
