from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ค่าตั้งของระบบ อ่านจากไฟล์ .env หรือจาก environment variable ของเครื่อง
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str

    jwt_algorithm: str
    jwt_expire_minutes: int


settings = Settings()
