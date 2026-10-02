#!/usr/bin/env python3
"""DueDate infrastructure (AWS CDK, Python). Mirrors the AWS Textract+Bedrock IDP
reference: a read-only, least-privilege, serverless, cheap-at-idle stack.

Resources:
  - Lambda (API): the backend pipeline (extract -> engine -> narrate -> aid)
  - Lambda Function URL: public HTTPS API endpoint (no login), CORS open for the SPA
  - S3 (uploads): short-TTL bucket for documents (24h lifecycle)  [optional path]
  - S3 (site) + CloudFront: the static frontend over HTTPS
  - IAM: Textract DetectDocumentText + Bedrock InvokeModel only (least privilege)
"""
import os
from aws_cdk import (
    App, Stack, Duration, CfnOutput, RemovalPolicy, BundlingOptions,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
)
from constructs import Construct

MODEL_ID = os.environ.get("DUEDATE_MODEL", "us.amazon.nova-2-lite-v1:0")
REGION = os.environ.get("CDK_DEFAULT_REGION", "us-east-1")


class DueDateStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kw):
        super().__init__(scope, cid, **kw)

        # --- short-TTL upload bucket (documents auto-deleted within 24h) ---
        uploads = s3.Bucket(
            self, "Uploads",
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(1))],
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET],
                              allowed_origins=["*"], allowed_headers=["*"])],
        )

        # --- API Lambda: bundle backend/ with boto3 (runtime provides boto3) ---
        api_fn = _lambda.Function(
            self, "Api",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=_lambda.Code.from_asset("../backend"),
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={"DUEDATE_MODEL": MODEL_ID, "UPLOAD_BUCKET": uploads.bucket_name},
        )

        # least-privilege: Textract read + Bedrock invoke only
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:DetectDocumentText", "textract:AnalyzeDocument"],
            resources=["*"]))
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            # Nova "us." IDs are cross-region inference profiles that route to the
            # foundation model in several regions; allow the profile AND the FMs.
            resources=[
                "arn:aws:bedrock:*::foundation-model/*",
                f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                f"arn:aws:bedrock:*:{self.account}:application-inference-profile/*",
            ]))
        uploads.grant_read(api_fn)

        fn_url = api_fn.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[_lambda.HttpMethod.POST, _lambda.HttpMethod.GET],
                allowed_headers=["content-type"]),
        )

        # --- static site: private S3 + CloudFront (OAC), HTTPS, SPA ---
        site = s3.Bucket(
            self, "Site",
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
        dist = cf.Distribution(
            self, "Cdn",
            default_root_object="index.html",
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cf.CachePolicy.CACHING_DISABLED),
            error_responses=[cf.ErrorResponse(http_status=403, response_http_status=200,
                                              response_page_path="/index.html")],
        )

        # inject the API URL into a tiny config.js the page reads before app logic
        s3deploy.BucketDeployment(
            self, "DeploySite",
            sources=[
                s3deploy.Source.asset("../frontend"),
                s3deploy.Source.data(
                    "config.js",
                    f'window.DUEDATE_API="{fn_url.url}";'),
            ],
            destination_bucket=site,
            distribution=dist, distribution_paths=["/*"],
        )

        CfnOutput(self, "ApiUrl", value=fn_url.url)
        CfnOutput(self, "SiteUrl", value=f"https://{dist.distribution_domain_name}")


app = App()
DueDateStack(app, "DueDate")
app.synth()
