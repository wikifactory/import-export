FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

WORKDIR /app/

RUN apt-get update \
  && apt-get install git libmagic1 --no-install-recommends -y \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --dev

COPY . /app
ENV PYTHONPATH=/app


