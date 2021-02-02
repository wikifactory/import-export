import app.models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# --------- Monkey patch db connection -----------------

test_db_name = "test"

db_string = "postgres://{}:{}@{}:{}".format(
    "wikifactory", "wikipass", "127.0.0.1", 8004
)

db_string = db_string + "/" + test_db_name


engine = create_engine(db_string)

app.models.Session = sessionmaker(bind=engine)

# ------------------------------------------------------

# Create all the tables inside the test db with the same structure
