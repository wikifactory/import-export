from app.model.element import Element, ElementType


def test_model_empty_creation():

    element = Element()

    assert element.id == ""
    assert element.type == ElementType.UNKNOWN
    assert len(element.children) == 0
    assert element.path == ""
