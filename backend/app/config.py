from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ค่าตั้งของระบบ อ่านจากไฟล์ .env หรือจาก environment variable ของเครื่อง

    คลาสนี้ทำหน้าที่ประกาศอย่างเดียวว่าระบบมีค่าตั้งอะไรบ้างและชนิดอะไร
    ค่าจริงทั้งหมดอยู่ที่ .env ที่เดียว จึงไม่มีฟิลด์ไหนมีค่าเริ่มต้น
    ถ้าขาดตัวใดตัวหนึ่ง แอปจะไม่ยอมสตาร์ตและฟ้องว่าขาดตัวไหน

    ตั้งใจให้เป็นแบบนั้น เพราะถ้าปล่อยให้ jwt_secret มีค่าเริ่มต้น
    วันที่ลืมสร้าง .env ระบบจะเดินหน้าต่อด้วยกุญแจที่ใครก็เดาได้
    แล้วปลอม token เข้าระบบเป็น admin ได้ทันที
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str

    jwt_algorithm: str
    jwt_expire_minutes: int


settings = Settings()
