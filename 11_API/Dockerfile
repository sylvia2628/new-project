FROM python:3.11-slim
WORKDIR /app
COPY app.py schema.sql README.md ./
RUN mkdir -p /app/data
ENV MUSE_HOST=0.0.0.0 MUSE_PORT=8787 MUSE_DB_PATH=/app/data/muse.db
EXPOSE 8787
CMD ["python", "app.py"]
