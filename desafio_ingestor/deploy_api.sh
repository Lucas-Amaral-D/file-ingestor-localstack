#!/bin/bash

REGION="us-east-1"
# Endpoint usado para comandos do awslocal rodando no host
HOST_ENDPOINT="http://localhost:4566"
# CORREÇÃO CRÍTICA: Endpoint usado DENTRO do container Lambda para acessar o LocalStack
INTERNAL_ENDPOINT="http://localstack:4566"
LAMBDA_NAME="ApiLambda"
ZIP_FILE="lambda_api.zip"

echo "--- 1. Empacotando o código Lambda da API ---"
cd desafio_ingestor/lambda_api || exit
zip -r ../../$ZIP_FILE . > /dev/null

echo "--- 2. Criando/Atualizando a Função Lambda da API ---"
awslocal lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.9 \
    --handler api_function.lambda_handler \
    --memory-size 128 \
    --timeout 30 \
    --zip-file fileb://../../$ZIP_FILE \
    --role arn:aws:iam::000000000000:role/irrelevant \
    --environment Variables="{LOCALSTACK_ENDPOINT=http://localstack:4566}"
    --endpoint-url $HOST_ENDPOINT \
    --region $REGION 2>/dev/null
    
awslocal lambda update-function-code \
    --function-name $LAMBDA_NAME \
    --zip-file fileb://../../$ZIP_FILE \
    --endpoint-url $HOST_ENDPOINT \
    --region $REGION 2>/dev/null
echo "Função Lambda da API criada/atualizada."

echo "--- 3. Criando o API Gateway ---"
API_NAME="FileIngestorAPI"
API_ID=$(awslocal apigateway get-rest-apis --endpoint-url $HOST_ENDPOINT --query "items[?name=='$API_NAME'].id" --output text)

if [ -z "$API_ID" ]; then
    API_ID=$(awslocal apigateway create-rest-api --name "$API_NAME" --endpoint-url $HOST_ENDPOINT --query 'id' --output text)
fi

ROOT_RESOURCE_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --endpoint-url $HOST_ENDPOINT --query 'items[?path==`/`].id' --output text)

echo "--- 4. Criando Recurso /files e /files/{id} ---"
FILES_RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_RESOURCE_ID --path-part "files" --endpoint-url $HOST_ENDPOINT --query 'id' --output text)
# Recurso filho para {id}
awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $FILES_RESOURCE_ID --path-part "{id}" --endpoint-url $HOST_ENDPOINT > /dev/null 

echo "--- 5. Configurando o Método GET /files e Integração Lambda ---"
# GET /files
awslocal apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $FILES_RESOURCE_ID \
    --http-method GET \
    --authorization-type NONE \
    --endpoint-url $HOST_ENDPOINT
    
# Integração Lambda PROXY para a Lambda da API
awslocal apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $FILES_RESOURCE_ID \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:000000000000:function:$LAMBDA_NAME/invocations \
    --endpoint-url $HOST_ENDPOINT

echo "--- 6. Deploy da API ---"
awslocal apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name dev \
    --endpoint-url $HOST_ENDPOINT > /dev/null
    
API_URL="http://localhost:4566/restapis/$API_ID/dev/_user_request_"
echo "API Gateway implantado. URL de acesso: $API_URL"
echo "API ID para testes: $API_ID"

cd ../..
rm $ZIP_FILE
echo "Deploy da API concluído!"
