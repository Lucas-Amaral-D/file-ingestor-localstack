import json
import os
import hashlib
import boto3
from datetime import datetime

# --- Configuração Boto3 ---
# A Lambda dentro do LocalStack é configurada automaticamente
# para se comunicar com os serviços do LocalStack sem endpoint_url explícito.
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# --- Variáveis de Ambiente ---
# Assume que estas variáveis foram configuradas no setup/docker-compose
TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'files')
BUCKET_PROCESSED = os.environ.get('S3_BUCKET_PROCESSED', 'ingestor-processed')

table = dynamodb.Table(TABLE_NAME)

def calculate_sha256(s3_object):
    """Calcula o SHA256 do objeto lendo o stream do S3."""
    sha256_hash = hashlib.sha256()
    # Leitura em pedaços para evitar sobrecarga de memória (requisito não-funcional de performance)
    for chunk in s3_object['Body'].iter_chunks():
        sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def handler(event, context):
    try:
        # 1. Extrair Metadados do Evento S3
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        
        # Ignora eventos que não sejam de arquivo (ex: criação de diretório)
        if object_key.endswith('/'):
            print('Skipping folder event.')
            return {'statusCode': 200, 'body': 'Skipping folder event.'}
        
        file_size = record['s3']['object']['size']
        etag = record['s3']['object']['eTag']
        
        print(f"Iniciando processamento: s3://{bucket_name}/{object_key}")

        # 2. Ler Objeto, Obter ContentType e Calcular Checksum
        # Necessário para calcular o checksum e obter metadados adicionais
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        checksum = calculate_sha256(response)
        content_type = response['ContentType']
        
        # 3. Gravar Item no DynamoDB (Status: RAW)
        pk_value = f"file#{object_key}"
        timestamp = datetime.now().isoformat()
        
        table.put_item(
            Item={
                'pk': pk_value,
                'bucket': bucket_name,
                'key': object_key,
                'size': file_size,
                'etag': etag,
                'status': 'RAW',
                'checksum': checksum,
                'createdAt': timestamp,
                'contentType': content_type
            }
        )
        print(f"Item registrado no DynamoDB com status RAW. PK: {pk_value}")

        # 4. Mover o Arquivo (Copia para 'processed', Apaga do 'raw')
        
        copy_source = {'Bucket': bucket_name, 'Key': object_key}
        new_key = f"processed/{object_key}" # Usa prefixo 'processed/' para organizar (requisito)
        
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=BUCKET_PROCESSED,
            Key=new_key
        )

        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        print(f"Arquivo movido de {bucket_name} para {BUCKET_PROCESSED}/{new_key}")

        # 5. Atualizar Item no DynamoDB (Status: PROCESSED)
        table.update_item(
            Key={'pk': pk_value},
            UpdateExpression="SET #s = :status_val, processedAt = :timestamp_val, #b = :bucket_val, #k = :key_val",
            ExpressionAttributeNames={
                '#s': 'status', # 'status' é uma palavra reservada e precisa de alias
                '#b': 'bucket',
                '#k': 'key'
            },
            ExpressionAttributeValues={
                ':status_val': 'PROCESSED',
                ':timestamp_val': datetime.now().isoformat(),
                ':bucket_val': BUCKET_PROCESSED,
                ':key_val': new_key
            }
        )
        print(f"Processamento concluído. Status atualizado para PROCESSED.")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'File processed successfully', 'pk': pk_value})
        }

    except Exception as e:
        print(f"ERRO CRÍTICO NO PROCESSAMENTO: {e}")
        # Em produção, você registraria o erro no DynamoDB ou enviaria para um Dead Letter Queue (DLQ)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
