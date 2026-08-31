FROM python:3.12.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source
COPY bot.py .

# Run as a non-root user
RUN useradd --create-home bot
USER bot

CMD ["python", "bot.py"]