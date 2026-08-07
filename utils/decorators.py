import logging
import traceback
from functools import wraps
from datetime import datetime

cooldowns = {}

def friendly_error(func):
    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        try:
            return await func(message, *args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {traceback.format_exc()}")
            await message.reply(f"❌ **Oops! Something went wrong.**\n\n"
                                f"Please try again later. If the problem persists, contact the owner.\n"
                                f"*Error details:* `{str(e)[:150]}`")
    return wrapper

def rate_limit(seconds):
    def decorator(func):
        @wraps(func)
        async def wrapper(message, *args, **kwargs):
            user_id = message.from_user.id
            now = datetime.now()
            if user_id in cooldowns and (now - cooldowns[user_id]).total_seconds() < seconds:
                remaining = int(seconds - (now - cooldowns[user_id]).total_seconds())
                await message.reply(f"⏳ Please wait {remaining} seconds.")
                return
            cooldowns[user_id] = now
            return await func(message, *args, **kwargs)
        return wrapper
    return decorator
