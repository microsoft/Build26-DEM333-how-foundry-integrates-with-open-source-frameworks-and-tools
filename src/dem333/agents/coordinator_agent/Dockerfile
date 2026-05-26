FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY agents/coordinator_agent ./agents/coordinator_agent

ENV PYTHONPATH=/app/src
EXPOSE 8088
CMD ["python", "agents/coordinator_agent/main.py"]
