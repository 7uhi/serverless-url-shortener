# Local verification record

- Runtime: Python 3.12.15.
- Automated suite: **59 tests passed** using `python -m pytest -q`.
- SAM template: **passed** offline `cfn-lint template.yaml` validation, including SAM transformation.
- Browser: Safari loaded the HTML/CSS/JavaScript frontend; creating a link succeeded, opening it redirected to the destination, and refreshing statistics changed the count from 0 to 1.
- HTTP integration: a real localhost server accepted a POST, returned a 302 Location on GET, and reported one visit through the statistics endpoint.
- DynamoDB: Moto-backed adapter and packaged Lambda entry-point tests passed; no live AWS database calls were made.
- Git: local `main` repository initialized; runtime data and virtual environment excluded.
- Local preview server stopped after verification. Run `python local_server.py` to restart it; SQLite data is preserved.

Initial localhost binding was blocked by the execution sandbox. After permission to bind localhost was granted, the complete suite passed. This was an environment restriction, not an application test failure.

Not yet verified: an actual AWS deployment, AWS-managed IAM restrictions at deployment time, live Lambda/API Gateway/DynamoDB integration, real AWS costs, or mobile-device browser behavior. Desktop browser verification was manual, not a JavaScript end-to-end automation suite. AWS resources and permissions were not changed.

## Deployment preparation — October 19, 2026

- Project relocated to `~/Developer/AWS/serverless-url-shortener`; working tree was clean before preparation.
- All 59 tests passed again; local cfn-lint validation passed again.
- Installed SAM CLI 1.168.0 and CloudFormation Guard 3.2.1 through Homebrew with user approval. Added pip to the project's Python 3.12 environment for SAM's dependency builder.
- Downloaded the official AWS Guard rules registry into ignored `.local/aws-guard-rules-registry`.
- Guard passed three applicable rules: `DYNAMODB_TABLE_MUST_BE_ENCRYPTED`, `IAM_POLICYDOCUMENT_NO_WILDCARD_RESOURCE`, and `CW_LOGGROUP_RETENTION_PERIOD_CHECK`. This is a scoped check, not a comprehensive security certification.
- SAM build succeeded for Python 3.12 / x86_64. Artifacts are in ignored `.aws-sam/build`; no upload occurred.
- Local profile Region confirmed as `us-east-2`. Identity verification found an expired login. Current project identity, plan, and credits must be reverified after sign-in.
- The AWS MCP connector returned an unknown-tool error; the installed AWS CLI remains the available fallback.
- No AWS changes made. Cloud deployment authorization is present; the separate `aws login --profile student-aws` confirmation is still pending.

Reproduce the local build (does not deploy):

```bash
SAM_CLI_TELEMETRY=0 PATH="$PWD/.venv/bin:$PATH" sam build --template-file template.yaml
```
