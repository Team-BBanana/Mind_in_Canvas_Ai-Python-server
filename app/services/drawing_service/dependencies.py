from app.services.drawing_service.drawing_service import DrawingService
from app.services.drawing_service.drawing_service_impl import DrawingServiceImpl

_drawing_service: DrawingService = None

def get_drawing_service() -> DrawingService:
    global _drawing_service
    if _drawing_service is None:
        _drawing_service = DrawingServiceImpl()
    return _drawing_service 