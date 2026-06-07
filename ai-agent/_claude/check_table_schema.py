"""Check actual table schemas in database."""
import sys
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'financemanage')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'yourpassword')

engine = create_engine(
    f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
)

inspector = inspect(engine)

tables = ['stock_filter_score', 'ai_trade_decision', 'safety_filter_result',
          'news_analysis', 'prophet_forecast']

print("="*80)
print("DATABASE TABLE SCHEMAS")
print("="*80)

for table_name in tables:
    if inspector.has_table(table_name):
        print(f"\n{table_name}:")
        print("-" * 40)
        for column in inspector.get_columns(table_name):
            nullable = "NULL" if column['nullable'] else "NOT NULL"
            print(f"  {column['name']:30s} {str(column['type']):20s} {nullable}")
    else:
        print(f"\n{table_name}: ❌ TABLE DOES NOT EXIST")

print("\n" + "="*80)
