import os


database_enabled = True

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_DB")

service_name = os.getenv("POSTGRES_SERVICE_NAME")

wikifactory_connection_url = os.getenv("WIKIFACTORY_CONNECTION_URL")
wikifactory_test_user_name = os.getenv("WIKIFACTORY_TEST_USER_NAME")

db_string = "postgres://{}:{}@{}:{}".format(user, password, service_name, port)
