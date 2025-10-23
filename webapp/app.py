from flask import Flask, request, render_template, redirect, url_for, send_file
import boto3
import requests
import time
import os

app = Flask(__name__)

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

API_URL = 'http://localhost:4566/restapis/qky2ndgsp7/dev/_user_request_/files'

RAW_BUCKET = 'ingestor-raw'
PROCESSED_BUCKET = 'ingestor-processed'

@app.route('/')
def index():
    try:
        files = requests.get(API_URL).json()
    except Exception as e:
        files = []
        print(f"Erro ao buscar arquivos da API: {e}")
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file:
        s3.upload_fileobj(file, RAW_BUCKET, file.filename)
        time.sleep(2)
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    path = f'/tmp/{filename}'
    try:
        s3.download_file(PROCESSED_BUCKET, filename, path)
        return send_file(path, as_attachment=True)
    except Exception as e:
        return f"Erro ao baixar o arquivo: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)

