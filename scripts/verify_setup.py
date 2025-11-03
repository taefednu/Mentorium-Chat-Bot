#!/usr/bin/env python3
"""
Environment setup verification script for Mentorium Chat Bot
"""
import asyncio
import os
import sys
from pathlib import Path

import redis
from dotenv import load_dotenv
from sqlalchemy import text

from mentorium_db.session import get_session
from mentorium_db.settings import DatabaseSettings

# Load .env from project root
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")


async def check_database():
    """Check database connection"""
    try:
        settings = DatabaseSettings()
        async with get_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def check_redis():
    """Check Redis connection"""
    try:
        r = redis.Redis(host="localhost", port=6379, db=0)
        r.ping()
        print("✓ Redis connection successful")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


async def check_openai_key():
    """Check OpenAI API key"""
    import os

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("BOT_OPENAI_API_KEY"))
        # Test with a simple model list call
        await client.models.list()
        print("✓ OpenAI API key valid")
        return True
    except Exception as e:
        print(f"✗ OpenAI API key check failed: {e}")
        return False


async def main():
    print("Checking Mentorium Chat Bot environment...\n")

    db_ok = await check_database()
    redis_ok = check_redis()
    openai_ok = await check_openai_key()

    print()
    if db_ok and redis_ok and openai_ok:
        print("✓ All checks passed! Environment is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
