# Source image
# FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
FROM python:3.7


RUN pip install uvicorn

# Set environment varibles
# ENV any val
ENV PYTHONPATH "/app"
ENV PORT=8000
EXPOSE ${PORT}
# Set the working dir
WORKDIR /app



# Install dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --dev

COPY ./app /app

WORKDIR /app/
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD uvicorn main:app --host 0.0.0.0 --port $PORT

