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

Not yet verified: an actual SAM build/deployment, AWS-managed IAM restrictions at deployment time, live Lambda/API Gateway/DynamoDB integration, real AWS costs, or mobile-device browser behavior. Desktop browser verification was manual, not a JavaScript end-to-end automation suite. AWS resources and permissions were not changed.
