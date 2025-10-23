from flask import Flask, request, redirect, url_for, render_template_string, send_file
import boto3
import io
import os

app = Flask(__name__)
BUCKET_NAME = 'meu-bucket-localstack'
AWS_ENDPOINT_URL = 'http://localhost:4566'
AWS_REGION = 'us-east-1'

# Configuração do Boto3 para o LocalStack
s3 = boto3.client(
    's3',
    endpoint_url=AWS_ENDPOINT_URL,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name=AWS_REGION
)

def setup_s3_bucket():
    # Cria o bucket se ele não existir
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except:
        s3.create_bucket(Bucket=BUCKET_NAME)

@app.route('/', methods=['GET', 'POST'])
def index():
    setup_s3_bucket()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            # Upload do arquivo
            s3.upload_fileobj(file, BUCKET_NAME, file.filename)
            return redirect(url_for('index'))

    # Lista de arquivos no bucket
    files = []
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        # Apenas para debug simples
        files = [f"Erro ao listar S3: {str(e)}"]

    # Template HTML simples
    html_template = """
    <!doctype html>
    <title>S3 LocalStack Files</title>
    <h1>Upload de Arquivo</h1>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file">
      <input type="submit" value="Upload">
    </form>
    <h2>Arquivos no S3: {{ bucket_name }}</h2>
    <ul>
    {% for file_key in files %}
      {% if not 'Erro' in file_key %}
        <li>{{ file_key }} - <a href="{{ url_for('download_file', filename=file_key) }}">Download</a></li>
      {% else %}
        <li>{{ file_key }}</li>
      {% endif %}
    {% endfor %}
    </ul>
    """
    return render_template_string(html_template, files=files, bucket_name=BUCKET_NAME)

@app.route('/download/<filename>')
def download_file(filename):
    try:
        # Recupera o arquivo do S3
        file_obj = s3.get_object(Bucket=BUCKET_NAME, Key=filename)
        file_stream = io.BytesIO(file_obj['Body'].read())
        return send_file(file_stream, download_name=filename, as_attachment=True, mimetype=file_obj['ContentType'])
    except Exception as e:
        return f"Erro ao baixar: {str(e)}", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
