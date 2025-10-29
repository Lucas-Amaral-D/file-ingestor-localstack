import json
import boto3
import hashlib
from datetime import datetime
import urllib.parse
import os

S3_ENDPOINT = os.environ.get('AWS_ENDPOINT_URL', 'http://localstack:4566')
DYNAMO_TABLE = 'files'
PROCESSED_BUCKET = 'ingestor-processed'

s3 = boto3.client('s3', endpoint_url=S3_ENDPOINT)
dynamodb = boto3.resource('dynamodb', endpoint_url=S3_ENDPOINT)
table = dynamodb.Table(DYNAMO_TABLE)

def calculate_sha256(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    sha256_hash = hashlib.sha256()
    with response['Body'] as file_stream:
        for chunk in iter(lambda: file_stream.read(4096), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def lambda_handler(event, context):
    try:
        record = event['Records'][0]
        bucket_raw = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
        
        response = s3.head_object(Bucket=bucket_raw, Key=key)
        size = response['ContentLength']
        etag = response['ETag'].strip('"')
        content_type = response.get('ContentType', 'unknown')
        
        checksum = calculate_sha256(bucket_raw, key)
        pk_value = f"file#{key}"
        
        # 1. Cria/atualiza item no DynamoDB com status RAW
        item = {
            'pk': pk_value, 'bucket': bucket_raw, 'key': key, 'size': size,
            'etag': etag, 'contentType': content_type, 'checksum': checksum,
            'status': 'RAW', 'createdAt': datetime.utcnow().isoformat()
        }
        table.put_item(Item=item)
        
        # 2. Move o arquivo para o bucket processado
        processed_key = f"processed/{key}"
        copy_source = {'Bucket': bucket_raw, 'Key': key}
        s3.copy_object(CopySource=copy_source, Bucket=PROCESSED_BUCKET, Key=processed_key)
        s3.delete_object(Bucket=bucket_raw, Key=key)
        
        # 3. Atualiza item no DynamoDB para PROCESSED
        table.update_item(
            Key={'pk': pk_value},
            UpdateExpression="SET #s = :status, processedAt = :pA, #k = :pKey, bucket = :pBucket",
            ExpressionAttributeNames={'#s': 'status', '#k': 'key'},
            ExpressionAttributeValues={
                ':status': 'PROCESSED', ':pA': datetime.utcnow().isoformat(),
                ':pKey': processed_key, ':pBucket': PROCESSED_BUCKET
            }
        )
        return {'statusCode': 200, 'body': f"Arquivo {key} processado."}
        
    except Exception as e:
        print(f"Erro ao processar arquivo: {str(e)}")
        return {'statusCode': 500, 'body': f'Erro: {str(e)}'}
