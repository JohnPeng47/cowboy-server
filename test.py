from cowboy_lib.repo.source_repo import SourceRepo
from src.test_modules.iter_tms import iter_test_modules
from src.test_modules.models import TestModuleModel
from pathlib import Path

from sqlalchemy.sql import text


from src.database.core import engine
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
query = text("""
    SELECT schema_name FROM information_schema.schemata
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    AND schema_name NOT LIKE 'pg_toast%'
    AND schema_name NOT LIKE 'pg_temp_%'
""")

# Execute the query
with engine.connect() as connection:
    # Query to get all tables from the public schema
    table_query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    # Execute the query to get all table names
    with engine.connect() as connection:
        tables = connection.execute(table_query).fetchall()
        
        # Iterate through each table and get its schema details
        for table in tables:
            table_name = table[0]
            print(f"\nSchema for table '{table_name}':")

            # Query to get schema details for each table
            schema_query = text(f"""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
            """)

            # Fetch and print the schema details for each table
            schema_details = connection.execute(schema_query, {'table_name': table_name}).fetchall()
            for detail in schema_details:
                print(detail)
                # print(f"Column Name: {detail['column_name']}, "
                #       f"Type: {detail['data_type']}, "
                #       f"Nullable: {detail['is_nullable']}, "
                #       f"Default: {detail['column_default']}")


# session = Session()
# tm = (
#     session.query(TestModuleModel)
#     .filter(TestModuleModel.name == "TestWoodpecker")
#     .filter(TestModuleModel.repo_id == 38)
#     .one_or_none()
# )

# print(tm.target_chunks)
# # s = SourceRepo(Path("repos/test2/upflwdnk"))
# # tms = iter_test_modules(s)
# # testing = []
# # for tm in tms:
# #     if tm.name != "TestWoodpecker":
# #         continue

# #     print(tm.name, tm.test_file.path)
