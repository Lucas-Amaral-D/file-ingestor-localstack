#!/bin/bash

# Este script será executado automaticamente pelo LocalStack na inicialização.

REGION="us-east-1"
ROLE_NAME="lambda-execution-role"
ROLE_ARN="arn:aws:iam::000000000000:role/${ROLE_NAME}"
INGEST_LAMBDA="ingest-file"
API_LAMBDA="files-api"

# --- Criação de Buckets S3 ---
awslocal s3 mb s3://ingestor-raw
awslocal s3 mb s3://ingestor-processed

# --- Criação da Tabela DynamoDB ---
awslocal dynamodb create-table \
    --table-name files \
    --attribute-definitions AttributeName=pk,AttributeType=S,AttributeName=processedAt,AttributeType=S \
    --key-schema AttributeName=pk,KeyType=HASH \
    --global-secondary-indexes '[{"IndexName": "ProcessedAtIndex", "KeySchema": [{"AttributeName": "processedAt", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}]' \
    --billing-mode PAY_PER_REQUEST

# --- Criação da Role IAM ---
awslocal iam create-role \
    --role-name ${ROLE_NAME} \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

awslocal iam put-role-policy \
    --role-name ${ROLE_NAME} \
    --policy-name s3-dynamodb-access \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["s3:*", "dynamodb:*", "logs:*"],
            "Resource": "*"
        }]
    }'

sleep 5

# --- Criação das Lambdas ---
cd /docker-entrypoint-initaws.d/src/ingest-lambda
zip -r /tmp/ingest-lambda.zip .

awslocal lambda create-function \
    --function-name ${INGEST_LAMBDA} \
    --runtime python3.9 \
    --zip-file fileb:///tmp/ingest-lambda.zip \
    --handler app.lambda_handler \
    --role ${ROLE_ARN}

cd /docker-entrypoint-initaws.d/src/api-lambda
zip -r /tmp/api-lambda.zip .

awslocal lambda create-function \
    --function-name ${API_LAMBDA} \
    --runtime python3.9 \
    --zip-file fileb:///tmp/api-lambda.zip \
    --handler app.lambda_handler \
    --role ${ROLE_ARN}

# --- Configuração do Trigger S3 ---
awslocal s3api put-bucket-notification-configuration \
    --bucket ingestor-raw \
    --notification-configuration '{
        "LambdaFunctionConfigurations": [{
            "Id": "IngestTrigger",
            "LambdaFunctionArn": "arn:aws:lambda:'"${REGION}"':000000000000:function:'"${INGEST_LAMBDA}"'",
            "Events": ["s3:ObjectCreated:*"]
        }]
    }'

# --- Configuração do API Gateway ---
API_NAME="files-api"
LAMBDA_URI="arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:000000000000:function:${API_LAMBDA}/invocations"

API_ID=$(awslocal apigateway create-rest-api --name ${API_NAME} --query "id" --output text)
ROOT_ID=$(awslocal apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/'].id" --output text)

FILES_RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part files --query "id" --output text)
ID_RESOURCE_ID=$(awslocal apigateway create-resource --rest-api-id $API_ID --parent-id $FILES_RESOURCE_ID --path-part '{id}' --query "id" --output text)

awslocal apigateway put-method --rest-api-id $API_ID --resource-id $FILES_RESOURCE_ID --http-method GET --authorization-type NONE
awslocal apigateway put-method --rest-api-id $API_ID --resource-id $ID_RESOURCE_ID --http-method GET --authorization-type NONE

awslocal apigateway put-integration --rest-api-id $API_ID --resource-id $FILES_RESOURCE_ID --http-method GET --type AWS_PROXY --integration-http-method POST --uri ${LAMBDA_URI}
awslocal apigateway put-integration --rest-api-id $API_ID --resource-id $ID_RESOURCE_ID --http-method GET --type AWS_PROXY --integration-http-method POST --uri ${LAMBDA_URI}

awslocal apigateway create-deployment --rest-api-id $API_ID --stage-name dev
