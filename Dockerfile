# kiwix-zhs-proxy — 简繁转换代理（只跑代理，Kiwix 服务在别处/宿主机）
# 构建：docker build -t kiwix-zhs-proxy .
# 运行（Kiwix 跑在宿主机 8090 时）：
#   docker run --rm -p 8080:8080 \
#     -e KIWIX_UPSTREAM=http://host.docker.internal:8090 \
#     -e KIWIX_HOST=0.0.0.0 \
#     kiwix-zhs-proxy
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kiwix_zhs_proxy.py .

EXPOSE 8080
ENV KIWIX_UPSTREAM=http://127.0.0.1:8090 \
    KIWIX_PORT=8080 \
    KIWIX_HOST=127.0.0.1

CMD ["python", "kiwix_zhs_proxy.py"]
