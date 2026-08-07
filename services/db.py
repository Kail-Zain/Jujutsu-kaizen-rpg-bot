async def get_player(user_id):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)

async def update_player_stats(user_id):
    # your existing logic
    pass
