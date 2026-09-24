from fastapi import Header, HTTPException
from pydantic import BaseModel


class User(BaseModel):
    user_id: str
    team: str
    permissions: list[str]


# In production: database lookup. Here: hardcoded for demo.
_API_KEYS: dict[str, User] = {
    "key-dev-001": User(
        user_id="dev1",
        team="backend",
        permissions=["code_analysis", "impact_analysis", "doc_generation"],
    ),
    "key-readonly-001": User(
        user_id="viewer1",
        team="product",
        permissions=["code_analysis"],
    ),
}


async def get_current_user(x_api_key: str = Header(...)) -> User:
    user = _API_KEYS.get(x_api_key)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return user
