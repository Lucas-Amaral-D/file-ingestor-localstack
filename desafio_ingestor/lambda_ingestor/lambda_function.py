import json
import os
import boto3
from datetime import datetime
import hashlib

# Obtém o endpoint de rede interno configurado no script de deploy
LOCALSTACK_ENDPOINT = os.environ.get('LOCALSTACK_ENDPOINT')

# Função auxiliar para calcular o checksum
def calculate_checksum(bucket, key):
    # Inicializa o cliente S3 para baixar o objeto
    s3_client = boto3.client('s3', endpoint_url=LOCALSTACK_ENDPOINT)
    
    # Baixa o objeto e calcula o SHA256
    s3_object = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = s3_object['Body'].read()
    
    # Retorna o checksum SHA256
    return hashlib.sha256(file_content).hexdigest()

def lambda_handler(event, context):
    try:
        # CORREÇÃO CRÍTICA: Inicialização correta dos clientes Boto3
        s3_client = boto3.client('s3', endpoint_url=LOCALSTACK_ENDPOINT)
        dynamodb = boto3.resource('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT)
        table = dynamodb.Table('files')

        record = event['Records'][0]['s3']
        source_bucket = record['bucket']['name']
        object_key = record['object']['key']
        
        # O ETag e o Size são redundantes, mas mantidos se forem usados em metadados.
        # e_tag = record['object']['eTag']
        size = record['object']['size'] 

        pk = f"file#{object_key}"
        processed_bucket = 'ingestor-processed'

        # Obter metadados e calcular checksum
        # O head_object foi corrigido para usar a sintaxe correta do cliente S3
        head_response = s3_client.head_object(Bucket=source_bucket, Key=object_key)
        content_type = head_response.get('ContentType', 'application/octet-stream')
        checksum = calculate_checksum(source_bucket, object_key)

        # 1. Gravar item RAW no DynamoDB (status INGESTED)
        table.put_item(
            Item={
                'pk': pk, 
                'bucket': source_bucket, 
                'key': object_key, 
                'size': size,
                'contentType': content_type,
                'checksum': checksum,
                'status': 'INGESTED',
                'createdAt': datetime.utcnow().isoformat()
            }
        )

        # 2. Move o arquivo para o bucket processado
        copy_source = {'Bucket': source_bucket, 'Key': object_key}
        s3_client.copy_object(
            CopySource=copy_source, 
            Bucket=processed_bucket, 
            Key=object_key
        )
        s3_client.delete_object(Bucket=source_bucket, Key=object_key)

        # 3. Atualiza o item para PROCESSED no DynamoDB
        current_time = datetime.utcnow().isoformat()
        table.update_item(
            Key={'pk': pk},
            UpdateExpression="SET #s = :status, processedAt = :time, #b = :bucketName",
            ExpressionAttributeNames={'#s': 'status', '#b': 'bucket'},
            ExpressionAttributeValues={
                ':status': 'PROCESSED', 
                ':time': current_time,
                ':bucketName': processed_bucket # Adicionado para corrigir a UpdateExpression
            }
        )

        return {'statusCode': 200, 'body': json.dumps({'message': f'File {object_key} processed successfully'})}

    except Exception as e:
        print(f"ERRO CRÍTICO NA LAMBDA INGESTOR: {e}")
        # Retornar o erro 500 para indicar falha
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
