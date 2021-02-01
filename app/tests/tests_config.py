test_db_name = "test"

test_db_string = "postgresql://{}:{}@{}:{}/{}".format(
    "wikifactory", "wikipass", "192.168.50.102", 8004, test_db_name
)
