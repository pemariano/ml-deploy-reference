FROM ghcr.io/astral-sh/uv:0.12.23 AS uv

# Official AWS base image for Lambda with Python 3.13
FROM public.ecr.aws/lambda/python:3.13

# uv, used only at build time to install the locked dependencies
COPY --from=uv /uv /bin/uv

WORKDIR ${LAMBDA_TASK_ROOT}

# Dependencies (separate layer for efficient caching).
# Installs only production dependencies, exactly as pinned in uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project -o requirements.txt \
    && uv pip install --system --no-cache -r requirements.txt \
    && rm requirements.txt

# Application code: the handler stays at the task root, the model package under src/
COPY app/app.py ./
COPY src/ ./src/

# Pre-train the model at build time, with the same libraries used at runtime.
# In production, prefer loading the artifact from S3 via MODEL_PATH.
ENV MODEL_PATH=${LAMBDA_TASK_ROOT}/model.joblib
RUN python -c "from src.model import train; train(); print('Placeholder model trained successfully.')"

# Handler: file.function
CMD ["app.handler"]