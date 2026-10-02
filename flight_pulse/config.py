"""Environment-backed configuration for Flight Pulse."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _required(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True, slots=True)
class AeroDataBoxSettings:
    rapidapi_key: str
    rapidapi_host: str

    @classmethod
    def from_env(cls) -> "AeroDataBoxSettings":
        load_dotenv()
        return cls(
            rapidapi_key=_required("AERODATABOX_API_KEY"),
            rapidapi_host=os.getenv(
                "AERODATABOX_API_HOST",
                "aerodatabox.p.rapidapi.com",
            ),
        )


@dataclass(frozen=True, slots=True)
class MySQLSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "MySQLSettings":
        load_dotenv()

        port_text = os.getenv("MYSQL_PORT", "3306")
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError("MYSQL_PORT must be an integer") from exc

        return cls(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=port,
            database=_required("MYSQL_DATABASE"),
            user=_required("MYSQL_USER"),
            password=_required("MYSQL_PASSWORD"),
        )


@dataclass(frozen=True, slots=True)
class GeminiSettings:
    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "GeminiSettings":
        load_dotenv()
        return cls(
            api_key=_required("GEMINI_API_KEY"),
            model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        )
