"""Storage adapters: SQLite for local work, DynamoDB only inside Lambda."""
import json
import sqlite3
from pathlib import Path


class SQLiteStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS items (pk TEXT PRIMARY KEY, data TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def create(self, item):
        try:
            with self.connect() as db:
                db.execute('INSERT INTO items VALUES (?, ?)', (item['pk'], json.dumps(item)))
            return True
        except sqlite3.IntegrityError:
            return False

    def get(self, code):
        with self.connect() as db:
            row = db.execute('SELECT data FROM items WHERE pk = ?', (code,)).fetchone()
        return json.loads(row[0]) if row else None

    def visit(self, code, now):
        # A write transaction serializes concurrent increments, just as ADD does in DynamoDB.
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM items WHERE pk = ?', (code,)).fetchone()
            item = json.loads(row[0]) if row else None
            if not item or item['expires_at'] <= now:
                return None
            item['visits'] += 1
            db.execute('UPDATE items SET data = ? WHERE pk = ?', (json.dumps(item), code))
            return item

    def consume_limit(self, key, maximum, expires_at, now):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            # Emulate TTL cleanup for local rate-limit rows only.
            db.execute("DELETE FROM items WHERE pk LIKE 'rate#%' AND json_extract(data, '$.expires_at') <= ?", (now,))
            row = db.execute('SELECT data FROM items WHERE pk = ?', (key,)).fetchone()
            item = json.loads(row[0]) if row else {'pk': key, 'count': 0, 'expires_at': expires_at}
            if item['count'] >= maximum:
                return False
            item['count'] += 1
            db.execute('INSERT OR REPLACE INTO items VALUES (?, ?)', (key, json.dumps(item)))
            return True


class DynamoStore:
    def __init__(self, table):
        self.table = table

    def create(self, item):
        from boto3.dynamodb.conditions import Attr
        try:
            self.table.put_item(Item=item, ConditionExpression=Attr('pk').not_exists())
            return True
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False

    def get(self, code):
        return self.table.get_item(Key={'pk': code}, ConsistentRead=True).get('Item')

    def visit(self, code, now):
        from boto3.dynamodb.conditions import Attr
        try:
            return self.table.update_item(
                Key={'pk': code}, UpdateExpression='ADD visits :one',
                ExpressionAttributeValues={':one': 1},
                ConditionExpression=Attr('pk').exists() & Attr('expires_at').gt(now),
                ReturnValues='ALL_NEW',
            )['Attributes']
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return None

    def consume_limit(self, key, maximum, expires_at, now):
        from boto3.dynamodb.conditions import Attr
        try:
            self.table.update_item(
                Key={'pk': key},
                UpdateExpression='SET expires_at = :expiry ADD #count :one',
                ExpressionAttributeNames={'#count': 'count'},
                ExpressionAttributeValues={':expiry': expires_at, ':one': 1},
                ConditionExpression=Attr('count').not_exists() | Attr('count').lt(maximum),
            )
            return True
        except self.table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
