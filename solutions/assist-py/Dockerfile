FROM python:3.11-slim

LABEL maintainer="andreev@lab.local"
LABEL version="1.0"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/

EXPOSE 8098

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8098"]
