# Proof: a coding agent connected to AWS built and deployed DueDate

This documents the AWS Zero to Shipped requirement that a coding agent was connected to AWS,
with evidence of the connection and the deploy. Everything below is from the real build.

## The agent and the connection
- **Agent:** an AI coding agent (CLI), connected to AWS through the Agent Toolkit for AWS and AWS MCP servers.
- **AWS identity used:** IAM principal `arn:aws:iam::<your-account-id>:user/server` in `us-east-1`
  (verified with `aws sts get-caller-identity`).
- **Model access confirmed live:** the agent invoked Amazon Bedrock `us.amazon.nova-2-lite-v1:0`
  and received a response before any app code depended on it, and confirmed Amazon Textract
  was reachable in the same account and region.

## What the agent did, in order (spec-driven)
1. Wrote the design/steering doc (`docs/design-principles.md`) to tailor itself to the task.
2. Wrote the EARS requirements (`spec/duedate.md`) before any code.
3. Built the deterministic trust engine (`backend/engine.py`) and a trust-contract test
   suite (`tests/test_engine.py`), then ran it: 8 of 8 passing.
4. Built the guardrailed Amazon Bedrock narration layer (`backend/narrate.py`) and verified
   it live against Bedrock in English and Spanish.
5. Built the Amazon Textract adapter (`backend/extract.py`) and the Lambda handler
   (`backend/handler.py`).
6. Authored the AWS CDK stack (`infra/app.py`), bootstrapped the account, and deployed.
7. Verified the live app end to end in a real browser, found and fixed two deployment bugs
   (a Bedrock inference-profile IAM scope, and a duplicated CORS header), and redeployed.

## The deploy (real outputs)
CloudFormation stack: `DueDate` in `us-east-1`.

```
DueDate.ApiUrl  = https://uougs7e24fd5mcaahsoeaj557i0ebnyl.lambda-url.us-east-1.on.aws/
DueDate.SiteUrl = https://d3pjdlu332prje.cloudfront.net
```

Live resources created by the stack (from `aws cloudformation describe-stack-resources`):
- AWS::CloudFront::Distribution (+ OriginAccessControl)
- AWS::Lambda::Function (API) + AWS::Lambda::Url + Layer + Permissions
- AWS::S3::Bucket x2 (static site, and short-TTL uploads) + BucketPolicies
- AWS::IAM::Role x3 + AWS::IAM::Policy x2 (least privilege: Textract read + Bedrock invoke)

## Least-privilege IAM (the only non-logging permissions the API Lambda holds)
- `textract:DetectDocumentText`, `textract:AnalyzeDocument`
- `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- read on the uploads bucket only

## How to re-verify the connection yourself
```bash
aws sts get-caller-identity --region us-east-1
aws bedrock-runtime converse --region us-east-1 \
  --model-id us.amazon.nova-2-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"say OK"}]}]'
curl -s -X POST "$DUEDATE_API_URL" -H 'Content-Type: application/json' \
  -d '{"text":"THREE-DAY NOTICE TO PAY RENT OR QUIT ... dated January 6, 2026.","language":"en"}'
```

> Screenshots of the coding-agent session invoking AWS MCP tools and the CloudFormation deploy are
> added alongside this file as they are captured during the demo recording.
