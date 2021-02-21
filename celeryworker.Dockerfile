FROM python:3.7

WORKDIR /app

# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --dev

# COPY ./app /app
ENV PYTHONPATH=/app

COPY ./scripts/worker-start.sh /app/worker-start.sh

RUN chmod +x /app/worker-start.sh

CMD ["bash", "/app/worker-start.sh"]
