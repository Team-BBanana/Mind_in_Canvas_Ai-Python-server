import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.drawing_service.drawing_service_impl import DrawingServiceImpl


@pytest.fixture
def drawing_service():
    return DrawingServiceImpl()
