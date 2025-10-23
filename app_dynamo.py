from flask import Flask, request, redirect, url_for, render_template_string
import boto3
import hashlib
import os

app = Flask(__name__)
TABLE_NAME = 'Users'
AWS_ENDPOINT_URL = 'http://localhost:4566'
AWS_REGION = 'us-east-1'

# Configuração do Boto3 para o LocalStack
dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name=AWS_REGION
)

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def setup_dynamodb_table():
    client = boto3.client(
        'dynamodb',
        endpoint_url=AWS_ENDPOINT_URL,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=AWS_REGION
    )
    
    try:
        client.describe_table(TableName=TABLE_NAME)
    except client.exceptions.ResourceNotFoundException:
        print(f"Criando tabela {TABLE_NAME}...")
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        # Espera a tabela estar ativa no LocalStack
        waiter = client.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)
        print(f"Tabela {TABLE_NAME} criada com sucesso.")

@app.route('/register', methods=['GET', 'POST'])
def register():
    setup_dynamodb_table()
    table = dynamodb.Table(TABLE_NAME)
    message = ''
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)

        try:
            table.put_item(
                Item={
                    'username': username,
                    'password_hash': hashed_password
                },
                ConditionExpression='attribute_not_exists(username)'
            )
            message = 'Usuário cadastrado com sucesso! Tente fazer login.'
        except Exception as e:
            message = 'Erro: Usuário já existe ou falha no DynamoDB.'

    html_template = """
    <!doctype html>
    <title>Cadastro de Usuário - DynamoDB LocalStack</title>
    <h1>Cadastro de Usuário</h1>
    <p>{{ message }}</p>
    <form method="POST">
      <label for="username">Usuário:</label><br>
      <input type="text" id="username" name="username" required><br><br>
      <label for="password">Senha:</label><br>
      <input type="password" id="password" name="password" required><br><br>
      <input type="submit" value="Cadastrar">
    </form>
    <p><a href="{{ url_for('login') }}">Fazer Login</a></p>
    """
    return render_template_string(html_template, message=message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    setup_dynamodb_table()
    table = dynamodb.Table(TABLE_NAME)
    message = ''

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        try:
            response = table.get_item(Key={'username': username})
            
            if 'Item' in response:
                user = response['Item']
                if user['password_hash'] == hashed_password:
                    message = f'Autenticação bem-sucedida! Bem-vindo, {username}.'
                else:
                    message = 'Falha na autenticação: Senha incorreta.'
            else:
                message = 'Falha na autenticação: Usuário não encontrado.'
        except Exception as e:
            message = 'Erro ao consultar DynamoDB.'

    html_template = """
    <!doctype html>
    <title>Login de Usuário - DynamoDB LocalStack</title>
    <h1>Login de Usuário</h1>
    <p>{{ message }}</p>
    <form method="POST">
      <label for="username">Usuário:</label><br>
      <input type="text" id="username" name="username" required><br><br>
      <label for="password">Senha:</label><br>
      <input type="password" id="password" name="password" required><br><br>
      <input type="submit" value="Login">
    </form>
    <p><a href="{{ url_for('register') }}">Cadastrar</a></p>
    """
    return render_template_string(html_template, message=message)

@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
