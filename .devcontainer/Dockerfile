FROM mcr.microsoft.com/devcontainers/python:3.11

# ChromeとChromedriverをインストール
RUN apt-get update && apt-get install -y \
    chromium chromium-driver fonts-ipafont \
    && rm -rf /var/lib/apt/lists/*

# Pythonライブラリ
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ユーザー設定
USER vscode
WORKDIR /workspace
