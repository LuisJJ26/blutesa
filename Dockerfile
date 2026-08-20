# Kardex BLUTESA — imagen para probar en la red local de la empresa.
# No es una imagen de producción endurecida (usa el servidor de desarrollo de Django a
# propósito, para que estáticos/medios funcionen sin configurar un servidor aparte).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8030

ENTRYPOINT ["./entrypoint.sh"]
