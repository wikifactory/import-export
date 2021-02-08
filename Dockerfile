FROM python:3.7.4-slim

RUN apt-get update \
    && apt-get install git libmagic1 --no-install-recommends -y \
    && rm -rf /var/lib/apt/lists/*
RUN pip install uvicorn

# Set environment varibles
# ENV any val
ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV PORT=8000
EXPOSE ${PORT}
# Set the working dir
WORKDIR /app/



# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --dev


COPY ./app /app/app

CMD uvicorn app.main:fastapi_app --host 0.0.0.0 --port $PORT

