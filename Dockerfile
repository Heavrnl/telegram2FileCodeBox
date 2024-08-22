FROM python:3.9-slim

WORKDIR /app

# 直接安装所需的库
RUN pip install --no-cache-dir python-telegram-bot requests

COPY . .

CMD ["python", "app.py"]