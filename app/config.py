from typing import List, Optional

from pydantic import BaseSettings


class Config(BaseSettings):
    TOKEN: str
    ADMINS: str


config = Config()

__all__ = ['config']
