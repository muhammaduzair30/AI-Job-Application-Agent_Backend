"""Test all pooler combinations with new password."""
import asyncio
import asyncpg

async def test(label, **kwargs):
    try:
        conn = await asyncpg.connect(**kwargs, timeout=15)
        v = await conn.fetchval("SELECT version()")
        print(f"{label}: SUCCESS - {v[:50]}")
        await conn.close()
    except Exception as e:
        print(f"{label}: FAILED - {type(e).__name__}: {e}")

async def main():
    combos = [
        ("Session(5432) + postgres.ref", dict(user="postgres.ewrqazwiufcfgfscewzj", password="uzair2542khan", host="aws-0-ap-south-1.pooler.supabase.com", port=5432, database="postgres")),
        ("Transaction(6543) + postgres.ref", dict(user="postgres.ewrqazwiufcfgfscewzj", password="uzair2542khan", host="aws-0-ap-south-1.pooler.supabase.com", port=6543, database="postgres")),
        ("Session(5432) + postgres", dict(user="postgres", password="uzair2542khan", host="aws-0-ap-south-1.pooler.supabase.com", port=5432, database="postgres")),
        ("Transaction(6543) + postgres", dict(user="postgres", password="uzair2542khan", host="aws-0-ap-south-1.pooler.supabase.com", port=6543, database="postgres")),
    ]
    for label, kwargs in combos:
        print(f"Testing {label}...")
        await test(label, **kwargs)

asyncio.run(main())
