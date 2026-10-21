# Live deployment

Application: **https://oe8duuof0f.execute-api.us-east-2.amazonaws.com**

The shorter public frontend is now **https://yuhirl.netlify.app/**, published October 20, 2026. It proxies link operations to this AWS deployment. See [Netlify details](NETLIFY.md), including its HEAD counting behavior.

Deployed October 19, 2026 to the Blank Canvas project, Region **us-east-2**, using profile **student-aws**. The Free plan was verified active with $100 credits before deployment. No upgrade was performed.

## Resources

| Resource | Name |
| --- | --- |
| Application CloudFormation stack | `small-link` |
| SAM artifact CloudFormation stack | `aws-sam-cli-managed-default` |
| Lambda | `small-link-AppFunction-NwlemfI86CGo` |
| HTTP API | `oe8duuof0f` |
| DynamoDB table | `small-link-LinksTable-9CJXD99XY2NY` |
| Application log group | `small-link-AppLogs-PhfbXo58BKVp` |
| API log group | `small-link-ApiLogs-eQtEyDxqQPZ8` |
| Private artifact bucket | `aws-sam-cli-managed-default-samclisourcebucket-zadnl2e3ewp4` |

The application stack also manages its Lambda execution role, API stage, and API-to-Lambda permissions. The execution role remains scoped to table item operations and its application log streams. Public link creation is enabled; `AllowedHosts` is empty. This remains an unauthenticated learning demo with the limitations in [SECURITY.md](SECURITY.md).

## Test it yourself

Open the app, create a link to a public website, open the returned short link, and select **Refresh counts**. The URL currently uses an API Gateway hostname, so the complete link may be longer than a short destination. A custom short domain is a separate future feature with registration and DNS considerations.

The repeatable smoke test makes HTTPS requests and creates **one new expiring demo link** each time:

```bash
cd ~/Developer/AWS/serverless-url-shortener
.venv/bin/python scripts/smoke_test.py https://oe8duuof0f.execute-api.us-east-2.amazonaws.com
```

It does not follow the external destination or delete data. It checks status codes, the Location header, visits, HEAD behavior, validation, and static assets. Repeated runs consume the creation quota and AWS usage.

## Learn from CloudWatch

In the AWS Management Console, select **Ohio / us-east-2**, open CloudWatch → Logs → Log groups, and inspect the application group above. Look for `sdk_initialized` and `request_complete`, and the Lambda `REPORT` lines.

The first deployment used 128 MB and timed out after 10 seconds during startup. The deployed fix uses 512 MB and a 15-second timeout. More memory also gives Lambda more CPU. The timing logs showed SDK initialization completing in about 2.8 seconds afterward, and a warm redirect in about 7 ms. This is a concrete example of using production evidence to tune a serverless function instead of assuming that passing local tests proves cloud readiness.

Application and API logs retain seven days. Built-in Lambda/API Gateway/DynamoDB metrics are available; no custom dashboard or alert notifications were created. A request after an idle period can still have cold-start latency.

## Read-only status commands

```bash
aws cloudformation describe-stacks --stack-name small-link \
  --profile student-aws --region us-east-2 \
  --query 'Stacks[0].{Status:StackStatus,Outputs:Outputs}'

aws logs tail small-link-AppLogs-PhfbXo58BKVp --since 10m \
  --profile student-aws --region us-east-2
```

If credentials expire, refresh them using your approved AWS sign-in workflow. Never paste credentials into the project or a conversation.

## Changes and cleanup

Future cloud changes require approval and a reviewed change set. The repository's `template.yaml` reflects the deployed configuration; `.aws-sam/build` is a generated artifact. Rebuild after source changes.

Leave the resources in place to keep the demo usable. If cleanup is requested, review both stacks and the artifact bucket first. The table has `DeletionPolicy: Retain`, so deleting the application stack would retain it; the artifact bucket may also contain deployment packages. Retained resources can continue consuming credits. No automatic cleanup or deletion has been performed or scheduled.
