from app.models import Session


def test_database_connection():
    session = Session()
    assert session.execute("SELECT CURRENT_DATABASE()").scalar() == "dido_test"
