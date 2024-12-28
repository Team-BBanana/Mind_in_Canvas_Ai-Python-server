# OpenAI의 비동기 클라이언트를 임포트합니다.
# AsyncOpenAI 클래스는 OpenAI API와의 비동기 통신을 위한 클라이언트입니다.
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# 오픈AI API 호출 (텍스트 생성 모델)
async def call_openai_api(messages: list) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            # temperature=0.7,
            # max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"OpenAI API 호출 중 오류가 발생했습니다: {str(e)}")