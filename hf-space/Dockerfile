# FINN backend on a Hugging Face Space (Docker, free CPU). No card needed.
# The Space holds only this file and README.md; the code is cloned from GitHub at build time.
# To pick up new code: Space → Settings → "Factory rebuild".
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user
RUN git clone --depth 1 https://github.com/fizzyappy/Finn.git finn
WORKDIR /home/user/finn/backend
RUN pip install --no-cache-dir --user -r requirements-cloud.txt
ENV PATH="/home/user/.local/bin:$PATH" FINN_DATA_DIR=/tmp/finn-data PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["uvicorn", "finn.api:app", "--host", "0.0.0.0", "--port", "7860"]
