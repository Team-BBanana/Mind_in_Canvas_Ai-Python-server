from pydantic_settings import BaseSettings

# Settings 클래스는 환경 변수를 관리하기 위한 클래스입니다.
# Pydantic의 BaseSettings를 상속받아 환경 변수를 타입-세이프하게 로드할 수 있습니다.
# 
# 내부 Config 클래스는 Pydantic의 규약으로,
# env_file 설정을 통해 .env 파일에서 환경 변수를 자동으로 로드합니다.
class Settings(BaseSettings):
    # OpenAI API 설정
    # OpenAI의 API를 사용하기 위한 인증 키입니다.
    # .env 파일에서 반드시 설정해야 합니다.
    OPENAI_API_KEY: str
    
    # 서버 기본 설정
    # APP_NAME: 서버 애플리케이션의 이름을 정의합니다.
    # DEBUG_MODE: 개발 환경에서 디버그 모드 활성화 여부를 설정합니다.
    APP_NAME: str = "Mind_in_Canvas_AI-Python-Server"
    DEBUG_MODE: bool = False
    
    class Config:
        env_file = ".env"


# Settings 클래스의 인스턴스를 생성하여 환경 변수에 접근할 수 있게 합니다
# settings 인스턴스는 모듈 레벨에서 생성되어 전역적으로 사용 가능합니다.
# Python의 모듈레벨의 객체 생성은 싱글톤으로 동작하기 때문에, 이 settings 객체는 어플리케이션 전체에서 동일한 인스턴스로 공유됩니다.
# 일반 객체 생성은 함수 안에서 만들어져야함.
settings = Settings()