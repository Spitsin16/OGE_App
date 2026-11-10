from asyncio import to_thread

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


async def hash_password(password: str) -> str:
    return await to_thread(password_hasher.hash, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    return await to_thread(password_hasher.verify, password, hashed_password)
