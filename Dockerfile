# Menggunakan image Python versi slim untuk mengurangi ukuran (surface attack area lebih kecil)
FROM python:3.11-slim

# Mencegah Python menulis file .pyc ke disk (menghemat ruang dan I/O)
ENV PYTHONDONTWRITEBYTECODE=1

# Memastikan output Python dikirim langsung ke terminal tanpa di-buffer (penting untuk logging container)
ENV PYTHONUNBUFFERED=1

# Menetapkan direktori kerja di dalam container
WORKDIR /app

# Menginstal dependensi sistem yang dibutuhkan untuk kompilasi library Python (seperti mysqlclient)
RUN apt-get update \
    && apt-get install -y default-libmysqlclient-dev build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Menyalin file requirements dan menginstalnya
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh kode sumber proyek ke dalam container
COPY . /app/