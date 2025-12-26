from pydantic import BaseModel, Field, ConfigDict


class Email(BaseModel):
    id: str
    threadId: str
    sender: str = Field(alias="from")
    subject: str
    date: str
    snippet: str
    body: str = ""

    model_config = ConfigDict(populate_by_name=True)
