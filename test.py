import redis.asyncio as redis
import os

REDIS_URL = os.getenv("redis://default:KtciazCZnQSiwszqAibnbEbxqAGqfnof@redis.railway.internal:6379")

async def test_redis_connection():
    try:
        client = redis.from_url(REDIS_URL)
        await client.ping()
        print("Successfully connected to Redis!")
    except Exception as e:
        print(f"Error connecting to Redis: {e}")

import asyncio
asyncio.run(test_redis_connection())
