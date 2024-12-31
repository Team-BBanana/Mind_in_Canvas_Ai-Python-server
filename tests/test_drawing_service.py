import pytest
from unittest.mock import AsyncMock, patch
from app.models.drawing import NewDrawingRequest, DoneDrawingRequest, ChatMessage
from app.services.drawing_service.drawing_service_impl import DrawingServiceImpl

# ✅ 공통 Mock 설정
@pytest.fixture
def mock_openai():
    with patch("app.services.drawing_service.drawing_service_impl.DrawingServiceImpl.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value={"choices": [{"message": {"content": "Mocked Response"}}]})
        mock_client.audio.speech.create = AsyncMock(return_value=AsyncMock(content=b"Mocked Audio"))
        mock_client.images.generate = AsyncMock(return_value=AsyncMock(data=[{"url": "https://generated.background/image.jpg"}]))
        yield mock_client


# 📝 Test: handle_new_drawing
@pytest.mark.asyncio
async def test_handle_new_drawing(mock_openai):
    drawing_service = DrawingServiceImpl()
    request = NewDrawingRequest(
        robot_id="robot_123",
        name="아이",
        age=5,
        canvas_id="canvas_123"
    )
    response = await drawing_service.handle_new_drawing(request)
    assert response == "success"
    assert "canvas_123" in drawing_service.drawing_data
    assert drawing_service.drawing_data["canvas_123"].prompt != ""
    assert drawing_service.drawing_data["canvas_123"].audio_data is not None


# 📝 Test: handle_done_drawing
@pytest.mark.asyncio
async def test_handle_done_drawing(mock_openai):
    drawing_service = DrawingServiceImpl()
    new_request = NewDrawingRequest(
        robot_id="robot_123",
        name="아이",
        age=5,
        canvas_id="canvas_123"
    )
    await drawing_service.handle_new_drawing(new_request)

    done_request = DoneDrawingRequest(
        canvas_id="canvas_123",
        image_url="https://example.com/image.png"
    )
    response = await drawing_service.handle_done_drawing(done_request)
    assert response == "success"
    drawing_data = drawing_service.drawing_data["canvas_123"]
    assert drawing_data.analysis != ""
    assert drawing_data.summary != ""
    assert drawing_data.drawing_name != ""
    assert drawing_data.image_id.startswith("https://generated.background")


# 📝 Test: 오류 처리
@pytest.mark.asyncio
async def test_handle_new_drawing_missing_key(mock_openai):
    drawing_service = DrawingServiceImpl()
    request = NewDrawingRequest(
        robot_id="",
        name="",
        age=None,
        canvas_id=""
    )
    response = await drawing_service.handle_new_drawing(request)
    assert response.startswith("error")


# 📝 Test: OpenAI API 모델 호출
@pytest.mark.asyncio
async def test_summarize_conversation(mock_openai):
    drawing_service = DrawingServiceImpl()
    chat_history = [
        ChatMessage(role="user", text="나는 나무를 그리고 싶어"),
        ChatMessage(role="assistant", text="정말 멋진 나무 그림이 될 것 같아요!")
    ]
    response = drawing_service._summarize_conversation(chat_history)
    assert "Mocked Response" in response


@pytest.mark.asyncio
async def test_analyze_final_image(mock_openai):
    drawing_service = DrawingServiceImpl()
    image_url = "https://example.com/sample_image.jpg"
    response = drawing_service._analyze_final_image(image_url)
    assert "Mocked Response" in response


@pytest.mark.asyncio
async def test_generate_drawing_name(mock_openai):
    drawing_service = DrawingServiceImpl()
    analysis = "행복함 감정이 느껴지는 숲 주제"
    summary = "아이와 나무 이야기를 나눴다"
    response = drawing_service._generate_drawing_name(analysis, summary)
    assert "Mocked Response" in response


@pytest.mark.asyncio
async def test_generate_background_image(mock_openai):
    drawing_service = DrawingServiceImpl()
    image_url = "https://example.com/sample_image.jpg"
    response = drawing_service._generate_background_image(image_url)
    assert response.startswith("https://generated.background")
