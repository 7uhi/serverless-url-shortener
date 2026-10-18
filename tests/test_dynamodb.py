"""DynamoDB adapter contract tests; Moto intercepts AWS requests in memory."""
import boto3
import pytest
from moto import mock_aws
from backend.app import Application
from backend.storage import DynamoStore
from tests.test_app import create, event


@pytest.fixture
def dynamo(monkeypatch):
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_EC2_METADATA_DISABLED', 'true')
    with mock_aws():
        db = boto3.resource('dynamodb', region_name='us-east-2')
        table = db.create_table(TableName='test-links', KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}],
                                AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}], BillingMode='PAY_PER_REQUEST')
        yield DynamoStore(table)


def test_dynamodb_application_flow(dynamo):
    app = Application(dynamo, 'https://short.example.com', clock=lambda: 1700000000)
    item = create(app)
    assert app.handle(event('GET', '/r/' + item['code']))['statusCode'] == 302
    assert dynamo.get(item['code'])['visits'] == 1
    assert app.handle(event('GET', '/api/links/' + item['code']))['statusCode'] == 200
    assert not dynamo.create(dynamo.get(item['code']))
    assert dynamo.visit('missing1', 1700000000) is None
    assert dynamo.visit(item['code'], item['expires_at']) is None
    assert dynamo.get(item['code'])['visits'] == 1


def test_dynamodb_limits(dynamo):
    for _ in range(3):
        assert dynamo.consume_limit('rate#60#1', 3, 180, 60)
    assert not dynamo.consume_limit('rate#60#1', 3, 180, 60)
    assert dynamo.consume_limit('rate#60#2', 3, 240, 120)


def test_packaged_lambda_entrypoint(dynamo, monkeypatch):
    import importlib
    import json
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / 'backend'))
    monkeypatch.setenv('TABLE_NAME', 'test-links')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-2')
    module = importlib.import_module('app')
    monkeypatch.setattr(module, '_application', None)
    request = event('POST', '/api/links', {'url': 'https://example.com'})
    request['requestContext']['domainName'] = 'api-id.execute-api.us-east-2.amazonaws.com'
    request['headers']['host'] = 'untrusted-host.example.com'
    result = module.lambda_handler(request, None)
    assert result['statusCode'] == 201
    item = json.loads(result['body'])
    assert item['short_url'].startswith('https://api-id.execute-api.us-east-2.amazonaws.com/r/')
    assert dynamo.get(item['code'])['visits'] == 0
