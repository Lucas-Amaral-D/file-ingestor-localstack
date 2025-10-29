import os
import boto3
from flask import Flask, request, redirect, render_template

app = Flask(__name__)

LOCALSTACK_ENDPOINT = os.environ.get('LOCALSTACK_ENDPOINT', 'http://localhost:4566')
S3_BUCKET_RAW = 'ingestor-raw'
DYNAMO_TABLE = 'files'

s3_client = boto3.client('s3', endpoint_url=LOCALSTACK_ENDPOINT)
dynamo_client = boto3.client('dynamodb', endpoint_url=LOCALSTACK_ENDPOINT)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return redirect(request.url)

        filename = file.filename

        try:
            s3_client.upload_fileobj(file, S3_BUCKET_RAW, filename)
            dynamo_client.put_item(
                TableName=DYNAMO_TABLE,
                Item={
                    'id': {'S': f'file-{filename}'},
                    'filename': {'S': filename},
                    'status': {'S': 'raw'}
                }
            )
            message = f"Arquivo '{filename}' enviado com sucesso!"
            return render_template('index.html', message=message, success=True)
        except Exception as e:
            return render_template('index.html', message=str(e), success=False)

    return render_template('index.html', message=None, success=None)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

