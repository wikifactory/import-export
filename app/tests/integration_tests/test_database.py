from app.models import Session

import sqlalchemy_utils


def database_is_empty(engine):

    table_names = engine.table_names()
    assert False, table_names
    assert False
    is_empty = table_names == []
    print(is_empty)
    return is_empty


def db_exists(engine):
    try:
        return sqlalchemy_utils.database_exists(engine.url)
    except Exception as e:
        print(e)
        return False


def test_database_connection():
    session = Session()
    assert session.execute("SELECT CURRENT_DATABASE()").scalar() == "dido_test"


"""
def test_db_test_no_created(setup_db_connection_):

    engine = setup_db_connection_[0]
    # Session = setup_db_connection_test_db[1]

    assert db_exists(engine) is False


def test_db_with_test_db(setup_db_connection_testdb):

    engine = setup_db_connection_testdb[0]

    assert db_exists(engine) is True
"""
