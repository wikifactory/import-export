FROM python:3.7

WORKDIR /app

# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --dev

# COPY ./app /app
ENV PYTHONPATH=/

COPY ./scripts/worker-start.sh /worker-start.sh

RUN chmod +x /worker-start.sh

CMD ["bash", "/worker-start.sh"]
