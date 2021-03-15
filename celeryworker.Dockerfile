FROM python:3.7

WORKDIR /app

COPY . /app
ENV PYTHONPATH=/app

# Install dependencies
RUN pip install pipenv
ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then pipenv install --system --dev ; else pipenv install --system ; fi"

CMD ["bash", "/app/worker-start.sh"]
