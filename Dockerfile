FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

ENV API_BASE_URL=https://api.groq.com/openai/v1
ENV MODEL_NAME=llama3-8b-8192
ENV HF_TOKEN=""

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]