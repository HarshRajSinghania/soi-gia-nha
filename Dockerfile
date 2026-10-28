FROM python:3.12-slim

# LightGBM needs OpenMP at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m app
WORKDIR /home/app/soi-gia-nha
COPY --chown=app pyproject.toml README.md ./
COPY --chown=app src ./src
RUN pip install --no-cache-dir ".[app]"
COPY --chown=app app ./app
COPY --chown=app .streamlit ./.streamlit

USER app
# Model files (~220 MB) are fetched from the GitHub release on first start.
ENV SOI_GIA_NHA_MODEL_DIR=/home/app/model
EXPOSE 7860
CMD ["streamlit", "run", "app/app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true"]
