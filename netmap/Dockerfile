FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends nmap traceroute iproute2 ca-certificates snmp \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/
COPY static/ /app/static/

ENV PYTHONUNBUFFERED=1
EXPOSE 8088
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('NETMAP_PORT','8088'), timeout=4)"

WORKDIR /app/app
CMD ["python", "main.py"]
