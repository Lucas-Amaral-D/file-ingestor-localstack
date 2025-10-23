import json
import os
import boto3
from decimal import Decimal # ESTA IMPORTAÇÃO É CRÍTICA!

# Obtém o endpoint de rede interno configurado
LOCALSTACK_ENDPOINT = os.environ.get('LOCALSTACK_ENDPOINT')

# FUNÇÃO CRÍTICA: Lida com a serialização de Decimal
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    # Adicione a checagem de datetime se você estiver usando-o na API, embora seja menos comum no scan
    # if isinstance(obj, datetime): 
    #     return obj.isoformat()
    raise TypeError

def lambda_handler(event, context):
    try:
        # INICIALIZAÇÃO CRÍTICA: Usando o endpoint corrigido
        dynamodb = boto3.resource('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT)
        table = dynamodb.Table('files')

        http_method = event.get('httpMethod')
        
        if http_method == 'GET':
            response = table.scan()
            items = response.get('Items', [])
            
            # Formata a saída
            file_list = []
            for item in items:
                file_list.append({
                    'key': item['key'],
                    'status': item['status'],
                    'size': item['size'],
                    'processedAt': item.get('processedAt'),
                    'createdAt': item.get('createdAt')
                })

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                # USO CRÍTICO: Serializador customizado
                'body': json.dumps(file_list, default=decimal_default)
            }
        
        return {'statusCode': 400, 'body': json.dumps({'message': f'Método {http_method} não suportado.'})}

    except Exception as e:
        print(f"ERRO CRÍTICO NA LAMBDA API: {e}")
        # Retorna o erro 500 para o API Gateway
        return {'statusCode': 500, 'body': json.dumps({'message': 'Internal server error', 'detail': str(e)})}
