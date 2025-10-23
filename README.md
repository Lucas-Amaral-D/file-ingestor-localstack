# 📁 File Ingestor - LocalStack

Um pipeline completo de ingestão de arquivos usando LocalStack, simulando serviços AWS (S3, Lambda, DynamoDB, API Gateway) localmente.

---

## 🎯 Objetivo

Construir um pipeline onde:

- Um arquivo é enviado a um bucket S3
- Uma função Lambda é disparada por evento `ObjectCreated`, extrai metadados e grava no DynamoDB
- A Lambda move o arquivo para um bucket "processado" e atualiza o status
- Uma API (API Gateway + Lambda) lista/consulta os itens no DynamoDB

---

## 🏗️ Arquitetura

┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐ │ Upload │───▶│ S3 Raw Bucket│───▶│ Lambda Ingest│───▶│ DynamoDB │ └─────────────┘ └──────────────┘ └─────────────┘ └─────────────┘ │ ▼ ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐ │ API │◀───│ API Gateway │◀───│ Lambda API │◀───│ DynamoDB │ └─────────────┘ └──────────────┘ └─────────────┘ └─────────────┘ │ ▼ ┌─────────────┐ │ S3 Processed│ └─────────────┘


---

## 🚀 Instalação e Execução

### 1. Clone e instale dependências

```
git clone https://github.com/Lucas-Amaral-D/file-ingestor-localstack.git
cd file-ingestor-localstack
npm install
```
### 2. Deploy completo (comando único)

```
npm run deploy
```
Esse comando irá:
Iniciar o LocalStack
Empacotar as funções Lambda
Criar toda a infraestrutura (S3, DynamoDB, Lambda, API Gateway)
Configurar triggers e permissões

### 3. Testar o pipeline

```
npm run test
```

Esse comando irá:
- Criar um arquivo de teste
- Fazer upload para o bucket S3
- Aguardar o processamento
- Verificar os resultados no DynamoDB
- Testar os endpoints da API

### 🎬 Demonstração Visual
Imagens do fluxo completo:

📤 docs/upload.png – Upload via interface web

🔄 docs/lambda-log.png – Logs da Lambda processando o arquivo

🗃️ docs/dynamodb-item.png – Item salvo no DynamoDB

🌐 docs/api-response.png – Resposta da API com metadados

### 🧪 Testes manuais

Upload via AWS CLI

```
export AWS_ENDPOINT_URL=http://localhost:4566
aws s3 cp meu-arquivo.txt s3://ingestor-raw/ --endpoint-url $AWS_ENDPOINT_URL
```
Verificar no DynamoDB
```
awslocal dynamodb scan --table-name files
```

Consultar API
```
curl "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/files"
```

### 🚀 Subir o sistema (deploy completo)
```
npm run deploy
```

### 🧹 Derrubar o sistema (limpeza total)
```
npm run teardown
```
