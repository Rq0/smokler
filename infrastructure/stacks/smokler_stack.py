import os

from aws_cdk import (
    aws_dynamodb as dynamodb,
    core as cdk,
    aws_cognito as cognito,
    aws_s3 as s3,
    aws_lambda as lambda_,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from chalice.cdk import Chalice

RUNTIME_SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), os.pardir, 'runtime')

LAMBDA_SOURCE_DIR = os.path.join(RUNTIME_SOURCE_DIR, 'lambda')


class SmoklerStack(cdk.Stack):
    chalice: Chalice
    user_table: dynamodb.Table
    user_pool: cognito.UserPool
    bucket: s3.Bucket
    cdn: cloudfront.Distribution

    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.app_name = self.node.try_get_context("app_name")
        self.stage_name = self.node.try_get_context("stage")
        self._add_cognito()
        self._add_chalice()
        self._create_ddb_table()
        self._add_s3()
        self._add_cognito_trigger()

    def _add_chalice(self):
        self.chalice = Chalice(
            self, f'{self.app_name}_{self.stage_name}_chalice',
            source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                'environment_variables': {
                    'COGNITO_USER_POOL_ARN': self.user_pool.user_pool_arn,
                    'APP_NAME': self.app_name
                }
            }
        )

    def _create_ddb_table(self):
        self.user_table = dynamodb.Table(
            self, f'{self.app_name}_{self.stage_name}_user_table',
            partition_key=dynamodb.Attribute(
                name='PK', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name='SK', type=dynamodb.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        self.user_table.grant_read_write_data(
            self.chalice.get_role('DefaultRole')
        )
        self.chalice.add_environment_variable(
            key='USER_TABLE_NAME',
            value=self.user_table.table_name,
            function_name='APIHandler'
        )

    def _add_cognito(self):
        """
        Sets up the cognito infrastructure with the user pool, custom domain
        and app client for use by the S3, lambda.
        """
        # Create the user pool that holds our users
        self.user_pool = cognito.UserPool(
            self, f'{self.app_name}_{self.stage_name}_user_pool',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                phone=False,
                preferred_username=False,
                username=False,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=True,
                phone=False
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=False,
                require_digits=False,
                require_uppercase=False,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            sign_in_case_sensitive=False,
            email=cognito.UserPoolEmail.with_cognito(self.node.try_get_context("support_email")),
            device_tracking=cognito.DeviceTracking(
                challenge_required_on_new_device=False,
                device_only_remembered_on_user_prompt=True
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(mutable=True, required=True),
                given_name=cognito.StandardAttribute(mutable=True, required=True),
                family_name=cognito.StandardAttribute(mutable=True, required=True)
            )
        )
        self.user_pool_app_client = cognito.UserPoolClient(
            self, f"{self.app_name}_{self.stage_name}_user_pool_app_client",
            user_pool=self.user_pool,
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    client_credentials=False,
                    authorization_code_grant=False,
                    implicit_code_grant=True
                ),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE]
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO,
            ],
        )
        self.identity_pool = cognito.CfnIdentityPool(
            self, f"{self.app_name}_{self.stage_name}_identity_pool",
            allow_unauthenticated_identities=True,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool.user_pool_id,
                    provider_name=provider.provider_name
                )
                for provider in self.user_pool.identity_providers
            ],
        )
        self.domain = cognito.UserPoolDomain(
            self, f'{self.app_name}_{self.stage_name}_user_pool_domain',
            user_pool=self.user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f'{self.app_name}-{self.stage_name}-user-pool-{self.account}-{self.region}'
            ),
        )

    def _add_s3(self):
        self.bucket = s3.Bucket(
            self, f'{self.app_name}_{self.stage_name}_media_bucket',
        )
        self.bucket.grant_read_write(
            self.chalice.get_role('DefaultRole')
        )
        self.chalice.add_environment_variable(
            key='MEDIA_BUCKET_NAME',
            value=self.bucket.bucket_name,
            function_name='APIHandler'
        )
        self.cdn = cloudfront.Distribution(
            self, f'{self.app_name}_{self.stage_name}_cloudfront_distribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.bucket)
            )
        )

    def _add_cognito_trigger(self):
        auto_confirm_function = lambda_.Function(
            self,
            "auto-create-user-function",
            code=lambda_.Code.from_asset(
                path=LAMBDA_SOURCE_DIR
            ),
            handler="triggers.sign_up_trigger",
            runtime=lambda_.Runtime.PYTHON_3_8,
        )
        auto_confirm_function.add_environment(
            'USER_TABLE_NAME',
            self.user_table.table_name
        )
        self.user_pool.add_trigger(
            operation=cognito.UserPoolOperation.PRE_SIGN_UP,
            fn=auto_confirm_function
        )
        self.user_table.grant_read_write_data(
            auto_confirm_function.role
        )
