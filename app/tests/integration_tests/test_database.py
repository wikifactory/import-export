import pytest
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..tests_config import test_db_string


def database_is_empty(engine):

    table_names = engine.table_names()
    assert False, table_names
    assert False
    is_empty = table_names == []
    print(is_empty)
    return is_empty


@pytest.fixture
def setup_db_connection():
    engine = create_engine(test_db_string)

    Session = sessionmaker(bind=engine)

    yield (engine, Session)


def test_db_connection(setup_db_connection):

    engine = setup_db_connection[0]
    # Session = setup_db_connection[1]

    # session = Session()

    assert database_is_empty(engine) is False
