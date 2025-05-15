FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install uv

COPY . /app

RUN uv venv && \
    uv pip install --upgrade pip && \
    uv sync

ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

CMD ["start-hoku"]