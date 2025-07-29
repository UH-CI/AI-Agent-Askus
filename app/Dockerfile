FROM python:3.10-slim

WORKDIR /app

# Install uv (fast dependency manager)
RUN pip install uv

# Copy the project files into the container
COPY . /app

# Create a virtual environment and install project dependencies + editable package
RUN uv venv && \
    uv pip install --upgrade pip && \
    uv pip install -e . && \
    uv pip install huggingface_hub[hf_xet]  # fix the warning from earlier

# Set the virtual environment as default
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Start the app via your script entrypoint
CMD ["start-hoku"]
