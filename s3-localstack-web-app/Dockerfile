# Usa uma imagem base Python
FROM python:3.11-slim

# Instala CURL (essencial para o entrypoint.sh) e libere a cache
RUN apt-get update && apt-get install -y curl --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação e o script de inicialização
COPY app.py .
COPY templates templates
COPY entrypoint.sh .

# Dá permissão de execução ao script
RUN chmod +x entrypoint.sh

# Expõe a porta que o Flask vai usar
EXPOSE 5000

# Usa o novo script como ponto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]

# O CMD é agora o argumento final para o entrypoint, mas não é estritamente necessário
CMD ["python", "app.py"]
