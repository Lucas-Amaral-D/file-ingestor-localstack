#!/bin/bash

# Define que o script deve sair imediatamente se um comando falhar
set -e

# Pausa inicial para garantir que a porta 4566 comece a abrir antes do primeiro curl
sleep 5

# --- CHECAGEM DE SAÚDE ROBUSTA (90 segundos de espera) ---
echo "=== AGUARDANDO LOCALSTACK ESTAR PRONTO (via CURL) ==="
MAX_WAIT=30
COUNT=0
# Usando 127.0.0.1 para maior compatibilidade de rede no host
HEALTH_URL="http://127.0.0.1:4566/health"
ENDPOINT="http://127.0.0.1:4566"

while [ $COUNT -lt $MAX_WAIT ]; do
    # Tenta obter o código de status HTTP
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)
    
    # 200 indica que o LocalStack está online e operacional
    if [ "$STATUS_CODE" = "200" ]; then
        echo -e "\nLocalStack está ONLINE! Iniciando teste de infraestrutura..."
        # Damos um pequeno delay extra para garantir que o provisionamento de serviços esteja completo
        sleep 5 
        break
    fi
    
    printf "."
    sleep 3
    COUNT=$((COUNT+1))
done

if [ $COUNT -ge $MAX_WAIT ]; then
    echo -e "\nERRO CRÍTICO: LocalStack não respondeu após 90 segundos na porta 4566. Verifique os logs do Docker."
    exit 1
fi
echo -e "\nLocalStack e recursos prontos."
# -----------------------------------------------------------------

# --- CONFIGURAÇÃO E TESTE DO PIPELINE ---

FILE_NAME="dados_$(date +%s).txt"
TEST_CONTENT="Conteúdo de teste para o pipeline - $(date)"
echo "$TEST_CONTENT" > $FILE_NAME

echo "=== 1. UPLOAD PARA S3 RAW (DISPARA LAMBDA) ==="
aws --endpoint-url=$ENDPOINT s3 cp $FILE_NAME s3://ingestor-raw/

echo "=== 2. VERIFICANDO UPLOAD NO RAW ==="
aws --endpoint-url=$ENDPOINT s3 ls s3://ingestor-raw/

echo "=== 3. AGUARDANDO PROCESSAMENTO (7s para o Lambda concluir) ==="
sleep 7

echo "=== 4. VERIFICANDO BUCKET RAW (DEVE ESTAR VAZIO APÓS O PROCESSAMENTO) ==="
aws --endpoint-url=$ENDPOINT s3 ls s3://ingestor-raw/

echo "=== 5. VERIFICANDO BUCKET PROCESSED (DEVE CONTER O ARQUIVO) ==="
aws --endpoint-url=$ENDPOINT s3 ls s3://ingestor-processed/ --recursive

echo "=== 6. CONSULTANDO METADADOS NO DYNAMODB (Scan Completo) ==="
aws --endpoint-url=$ENDPOINT dynamodb scan \
    --table-name files \
    --output json

echo "=== 7. CONSULTANDO ITEM ESPECÍFICO VIA API GATEWAY ==="
# O ID da API Gateway é obtido em tempo de execução
API_ID=$(aws --endpoint-url=$ENDPOINT apigateway get-rest-apis --query "items[?name=='files-api'].id" --output text)
FULL_URL="${ENDPOINT}/restapis/$API_ID/dev/_user_request_/files"

echo "API URL (Consulta por ID): ${FULL_URL}/${FILE_NAME}"
curl -s "${FULL_URL}/${FILE_NAME}" | jq .

# Limpeza de arquivo temporário
rm $FILE_NAME

echo "=== PIPELINE TESTADO COM SUCESSO ==="
