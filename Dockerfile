FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

COPY proto ./proto
COPY main.py ./
COPY app ./app

RUN mkdir -p ./app/generated

RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./app/generated \
    --grpc_python_out=./app/generated \
    ./proto/wallet.proto

EXPOSE 50051 8002

USER app

CMD ["python", "main.py"]