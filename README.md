# 🗂️ File Ingestor com LocalStack

Este projeto simula um pipeline de ingestão de arquivos utilizando Flask, LocalStack e AWS SDK. Ele permite o upload de arquivos via interface web, armazena os arquivos em buckets S3 simulados e registra metadados em uma tabela DynamoDB — tudo localmente, sem necessidade de conta AWS.

---

## 🚀 Comando único para subir e derrubar

### Subir o ambiente (build + rede + containers)

```bash
docker-compose down && docker-compose up -d --build
```

### Derrubar o ambiente

```bash
docker-compose down
```

## 🧠 Decisões técnicas
- LocalStack foi escolhido para simular serviços AWS localmente, permitindo testes sem custo.

- Flask oferece uma interface web simples para upload e uma API para consulta.

- O script entrypoint.sh aguarda o LocalStack estar pronto antes de iniciar o Flask.

- Os arquivos são enviados para o bucket ingestor-raw, movidos para ingestor-processed e registrados no DynamoDB com status atualizado.

## 🧪 Como testar o pipeline

### 1. Instale as dependências
- Docker

- Docker Compose

- AWS CLI v2

- Python 3.11 + venv (opcional para testes locais)

### 2. Suba os containers
```
docker-compose down && docker-compose up -d --build
```

### 3. Crie os recursos simulados
```
aws --endpoint-url=http://localhost:4566 s3 mb s3://ingestor-raw
aws --endpoint-url=http://localhost:4566 s3 mb s3://ingestor-processed

aws --endpoint-url=http://localhost:4566 dynamodb create-table \
  --table-name files \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### 4. Acesse a interface web
```
http://localhost:5000
```
Faça o upload de um arquivo qualquer.

## 🔁 Fluxo completo

### 1. Upload via interface web

- Arquivo enviado com sucesso

### 2. Arquivo listado no bucket ingestor-raw
```
aws --endpoint-url=http://localhost:4566 s3 ls s3://ingestor-raw/
```

### 3. Movimentação para ingestor-processed
```
aws --endpoint-url=http://localhost:4566 s3 mv s3://ingestor-raw/<arquivo> s3://ingestor-processed/
```

### 4. Atualização no DynamoDB
```
aws --endpoint-url=http://localhost:4566 dynamodb update-item \
  --table-name files \
  --key '{"id": {"S": "file-<arquivo>"}}' \
  --update-expression "SET #s = :newval" \
  --expression-attribute-names '{"#s": "status"}' \
  --expression-attribute-values '{":newval": {"S": "processed"}}'
```

### 5. Consulta ao DynamoDB
```
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name files \
  --output table
```

## 📸 Evidências de funcionamento

### Upload bem-sucedido via interface web
<img width="810" height="242" alt="image" src="https://github.com/user-attachments/assets/0a35fa2a-26cb-44f5-bc1d-25b225796765" />

### Arquivo listado no bucket ingestor-raw
<img width="810" height="242" alt="image" src="https://github.com/user-attachments/assets/c755e0c4-e118-41b4-b444-09d3fa109de7" />

### Arquivo movido para ingestor-processed
<img width="1322" height="193" alt="image" src="https://github.com/user-attachments/assets/e0539f21-65a9-4ba8-be4e-99f383f4bf51" />

### Item atualizado no DynamoDB com status processed
<img width="872" height="444" alt="image" src="https://github.com/user-attachments/assets/8c440d00-6899-4681-8c6c-84a08943b696" />

## 📂 Estrutura do projeto

```
├── docker-compose.yml
├── s3-localstack-web-app/
│   ├── app.py
│   ├── entrypoint.sh
│   ├── templates/
├── setup/
├── scripts/
├── src/
└── test-file.txt
```
