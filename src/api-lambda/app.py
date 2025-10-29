import json
import boto3
from boto3.dynamodb.conditions import Attr
from urllib.parse import unquote
import os

S3_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localstack:4566')
DYNAMO_TABLE = 'files'

dynamodb = boto3.resource('dynamodb', endpoint_url=S3_ENDPOINT)
table = dynamodb.Table(DYNAMO_TABLE)

def get_files(query_params):
    filter_expr = None
    limit = int(query_params.get('limit', 100))
    
    status = query_params.get('status')
    if status:
        filter_expr = Attr('status').eq(status)
    
    from_date = query_params.get('from')
    to_date = query_params.get('to')
    
    date_filter = None
    if from_date and to_date:
        date_filter = Attr('processedAt').between(from_date, to_date)
    elif from_date:
        date_filter = Attr('processedAt').gte(from_date)
    elif to_date:
        date_filter = Attr('processedAt').lte(to_date)
        
    if date_filter:
        filter_expr = date_filter if not filter_expr else filter_expr & date_filter
        
    scan_kwargs = {'Limit': limit}
    if filter_expr:
        scan_kwargs['FilterExpression'] = filter_expr

    response = table.scan(**scan_kwargs)
    
    return response.get('Items', [])

def get_file_by_id(file_id):
    if not file_id.startswith('file#'):
        file_id = f"file#{unquote(file_id)}"
        
    response = table.get_item(Key={'pk': file_id})
    return response.get('Item')

def lambda_handler(event, context):
    http_method = event.get('httpMethod')
    path = event.get('path')
    path_parameters = event.get('pathParameters', {})
    
    try:
        if http_method == 'GET' and path == '/files':
            items = get_files(event.get('queryStringParameters', {}))
            return {
                'statusCode': 200, 'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'files': items, 'count': len(items)})
            }
        
        elif http_method == 'GET' and path_parameters and 'id' in path_parameters:
            item = get_file_by_id(path_parameters['id'])
            if item:
                return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': json.dumps(item)}
            else:
                return {'statusCode': 404, 'body': json.dumps({'error': 'File not found'})}
        
        return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
