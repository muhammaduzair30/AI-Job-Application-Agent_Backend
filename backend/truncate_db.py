import asyncio
from sqlalchemy import text
from app.db.session import async_session_factory
from app.config import settings

async def truncate_tables():
    tables = [
        "job_applications",
        "analysis_results",
        "cvs",
        "jobs",
        "users"
    ]
    
    print(f"Connecting to database to truncate tables: {', '.join(tables)}")
    
    async with async_session_factory() as session:
        try:
            # Use CASCADE to handle foreign key constraints
            truncate_query = text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
            await session.execute(truncate_query)
            await session.commit()
            print("Successfully truncated all tables.")
        except Exception as e:
            await session.rollback()
            print(f"Error truncating tables: {e}")

if __name__ == "__main__":
    asyncio.run(truncate_tables())
