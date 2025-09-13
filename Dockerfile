FROM python:3.12.7-slim-bookworm

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN SITE_PACKAGES=$(python3 -c 'import site; print(site.getsitepackages()[0])') && \
    sed -i '/@deprecated("Use recognize method instead of recognize_song")/d' "$SITE_PACKAGES/shazamio/api.py"

COPY songId.py /app/
COPY tools /app/tools

CMD ["python3", "songId.py"]

#debug
#ENTRYPOINT ["/bin/sh", "-c", "while true; do sleep 100000000; done"]
