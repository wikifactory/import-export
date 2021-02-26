FROM python:3.7

WORKDIR /app

COPY . /app
ENV PYTHONPATH=/app
COPY ./worker-start.sh /worker-start.sh
RUN chmod +x /worker-start.sh

# Install dependencies
RUN pip install pipenv
ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then pipenv install --system --dev ; else pipenv install --system ; fi"

CMD ["bash", "/worker-start.sh"]
