from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cognodb_uri: str
    cognodb_user: str
    cognodb_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
