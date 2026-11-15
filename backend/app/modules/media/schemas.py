import uuid

from pydantic import BaseModel


class MediaResponse(BaseModel):
    id: uuid.UUID
    url: str
    width: int
    height: int
