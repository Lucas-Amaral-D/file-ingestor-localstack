#!/bin/bash

REGION="us-east-1"
# Endpoint usado para comandos do awslocal rodando no host
HOST_ENDPOINT="http://localhost:4566"
# CORREÇÃO CRÍTICA: Endpoint usado DENTRO do container Lambda para acessar o LocalStack
INTERNAL_ENDPOINT="http://localstack:4566"
LAMBDA_NAME="IngestorLambda"
S3_SOURCE_BUCKET="ingestor-raw"
ZIP_FILE="lambda_ingestor.zip"

echo "--- 1. Empacotando o código Lambda ---"
cd desafio_ingestor/lambda_ingestor || exit
zip -r ../../$ZIP_FILE . > /dev/null

echo "--- 2. Criando/Atualizando a Função Lambda ---"
awslocal lambda create-function \
    --function-name $LAMBDA_NAME \
    --runtime python3.9 \
    --handler lambda_function.lambda_handler \
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
echo "Função Lambda '$LAMBDA_NAME' criada/atualizada."

echo "--- 3. Configurando o Trigger S3:ObjectCreated (CORRIGIDO) ---"
# O comando s3api corrige o problema de sintaxe da sua awslocal
awslocal s3api put-bucket-notification-configuration \
    --bucket $S3_SOURCE_BUCKET \
    --notification-configuration '{
        "LambdaFunctionConfigurations": [
            {
                "LambdaFunctionArn": "arn:aws:lambda:'$REGION':000000000000:function:'$LAMBDA_NAME'",
                "Events": ["s3:ObjectCreated:*"]
            }
        ]
    }' \
    --endpoint-url $HOST_ENDPOINT \
    --region $REGION
echo "Trigger S3 configurado no bucket '$S3_SOURCE_BUCKET'."

cd ../..
rm $ZIP_FILE
echo "Deploy da Lambda de Ingestão concluído!"
