FROM python:3.12-slim

WORKDIR /app
COPY src ./src
COPY requirements.txt ./requirements.txt
COPY pyproject.toml ./pyproject.toml

RUN pip install --no-cache-dir -r requirements.txt

# Non-root for least privilege (matches Azure guidance)
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["python", "-m", "src.agent.service"]
