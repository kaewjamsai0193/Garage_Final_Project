from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ค่าตั้งของระบบ อ่านจากไฟล์ .env หรือจาก environment variable ของเครื่อง

    สองค่าแรกไม่มีค่าเริ่มต้น ถ้าไม่ได้ตั้งไว้ แอปจะไม่ยอมสตาร์ต
    ตั้งใจให้เป็นแบบนั้น เพราะถ้าปล่อยให้มีค่าเริ่มต้น วันที่ลืมสร้าง .env
    ระบบจะเดินหน้าต่อด้วยกุญแจที่ใครก็เดาได้แทนที่จะฟ้อง
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480


settings = Settings()
