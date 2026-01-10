from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_budgets as budgets,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_s3 as s3,
)
from constructs import Construct


class OctivaryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        site_bucket = s3.Bucket(
            self,
            'SiteBucket',
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
        )

        distribution = cloudfront.Distribution(
            self,
            'SiteDistribution',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
        )

        user_pool = cognito.UserPool(
            self,
            'UserPool',
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(email=cognito.StandardAttribute(required=True)),
        )

        user_pool_client = cognito.UserPoolClient(
            self,
            'UserPoolClient',
            user_pool=user_pool,
            generate_secret=False,
        )

        api_lambda = _lambda.Function(
            self,
            'ApiLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset('../backend'),
            handler='app.main.handler',
            memory_size=256,
            timeout=Duration.seconds(10),
            environment={
                'MAX_MONTHLY_COST': '50',
                'OCTIVARY_PAUSED': '0',
                'AUTH_REQUIRED': '1',
                'COGNITO_USER_POOL_ID': user_pool.user_pool_id,
                'COGNITO_CLIENT_ID': user_pool_client.user_pool_client_id,
                'COGNITO_REGION': Stack.of(self).region,
                'RATE_LIMIT_PER_MINUTE': '90',
                'CACHE_TTL_SECONDS': '120',
                'CACHE_MAX_ENTRIES': '256',
            },
        )

        http_api = apigw.HttpApi(
            self,
            'HttpApi',
            cors_preflight=apigw.CorsPreflightOptions(
                allow_headers=['*'],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_origins=['*'],
            ),
        )

        integration = apigw_integrations.HttpLambdaIntegration('ApiIntegration', api_lambda)
        http_api.add_routes(path='/{proxy+}', methods=[apigw.HttpMethod.ANY], integration=integration)
        http_api.add_routes(path='/', methods=[apigw.HttpMethod.ANY], integration=integration)

        saved_searches_table = dynamodb.Table(
            self,
            'SavedSearchesTable',
            partition_key=dynamodb.Attribute(
                name='search_id',
                type=dynamodb.AttributeType.STRING,
            ),
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndex(
                    index_name='UserIdIndex',
                    partition_key=dynamodb.Attribute(
                        name='user_id',
                        type=dynamodb.AttributeType.STRING,
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        users_table = dynamodb.Table(
            self,
            'UsersTable',
            partition_key=dynamodb.Attribute(
                name='user_id',
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        priority_events_table = dynamodb.Table(
            self,
            'AnonymousPriorityEventsTable',
            partition_key=dynamodb.Attribute(
                name='event_id',
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        api_lambda.add_environment('SAVED_SEARCHES_TABLE', saved_searches_table.table_name)

        saved_searches_table.grant_read_write_data(api_lambda)
        users_table.grant_read_write_data(api_lambda)
        priority_events_table.grant_read_write_data(api_lambda)

        guardrail_lambda = _lambda.Function(
            self,
            'GuardrailLambda',
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset('lambda'),
            handler='guardrail.handler',
            memory_size=128,
            timeout=Duration.seconds(10),
        )

        budget_alert_email = self.node.try_get_context('budgetAlertEmail')
        if budget_alert_email:
            budgets.CfnBudget(
                self,
                'MonthlyBudget',
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_type='COST',
                    time_unit='MONTHLY',
                    budget_limit=budgets.CfnBudget.SpendProperty(
                        amount=50,
                        unit='USD',
                    ),
                ),
                notifications_with_subscribers=[
                    budgets.CfnBudget.NotificationWithSubscribersProperty(
                        notification=budgets.CfnBudget.NotificationProperty(
                            comparison_operator='GREATER_THAN',
                            threshold=80,
                            threshold_type='PERCENTAGE',
                            notification_type='ACTUAL',
                        ),
                        subscribers=[
                            budgets.CfnBudget.SubscriberProperty(
                                address=budget_alert_email,
                                subscription_type='EMAIL',
                            )
                        ],
                    )
                ],
            )

        CfnOutput(self, 'CloudFrontUrl', value=f"https://{distribution.domain_name}")
        CfnOutput(self, 'ApiUrl', value=http_api.api_endpoint)
        CfnOutput(self, 'UserPoolId', value=user_pool.user_pool_id)
        CfnOutput(self, 'UserPoolClientId', value=user_pool_client.user_pool_client_id)
        CfnOutput(self, 'GuardrailLambdaName', value=guardrail_lambda.function_name)
