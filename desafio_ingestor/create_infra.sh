#!/bin/bash

REGION="us-east-1"
ENDPOINT="http://localhost:4566"

echo "--- 1. Verificando/Criando Buckets S3 ---"
awslocal s3 mb s3://ingestor-raw --endpoint-url $ENDPOINT --region $REGION 2>/dev/null || echo "Bucket ingestor-raw já existe."
awslocal s3 mb s3://ingestor-processed --endpoint-url $ENDPOINT --region $REGION 2>/dev/null || echo "Bucket ingestor-processed já existe."

echo "--- 2. Criando Tabela DynamoDB: files ---"
awslocal dynamodb create-table \
    --table-name files \
    --key-schema AttributeName=pk,KeyType=HASH \
    --attribute-definitions AttributeName=pk,AttributeType=S \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --endpoint-url $ENDPOINT \
    --region $REGION 2>/dev/null || echo "Tabela 'files' já existe."

echo "Infraestrutura básica criada/verificada."
