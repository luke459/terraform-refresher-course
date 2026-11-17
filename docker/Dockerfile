FROM node:22-bookworm-slim@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee AS web
WORKDIR /build/runner/web
COPY runner/web/package*.json ./
RUN npm ci --ignore-scripts
COPY runner/web/ ./
COPY curriculum/ /build/curriculum/
RUN node node_modules/typescript/bin/tsc --noEmit && node node_modules/vite/bin/vite.js build

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    TFPREP_ROOT=/app TFPREP_STATE=/var/lib/tfprep TFPREP_WORKSPACES=/workspaces \
    AWS_EC2_METADATA_DISABLED=true
WORKDIR /app
COPY docker/toolchain.json docker/toolchain.json
COPY scripts/install_runtime.py scripts/install_runtime.py
RUN python scripts/install_runtime.py
COPY requirements.lock ./
RUN pip install --requirement requirements.lock
COPY pyproject.toml ./
COPY runner/ runner/
COPY curriculum/ curriculum/
COPY exam-bank/ exam-bank/
COPY schemas/ schemas/
COPY scripts/ scripts/
COPY objective-coverage.csv README.md ./
COPY .tflint.hcl ./
COPY --from=web /build/runner/web/dist runner/web/dist
RUN pip install --no-deps --no-build-isolation . && tflint --init && \
    mkdir -p /workspaces /var/lib/tfprep && chmod 700 /workspaces /var/lib/tfprep
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2)"
CMD ["uvicorn", "runner.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
