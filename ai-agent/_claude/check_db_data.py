#!/usr/bin/env python3
"""Check current database data and UNIQUE constraints."""

import psycopg2
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'financemanage')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'yourpassword')

def check_table_data():
    """Check data in key tables."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    print("=" * 80)
    print("DATABASE DATA CHECK")
    print("=" * 80)

    tables = [
        ('stock_filter_score', 'score_date'),
        ('stock_financial', 'base_date'),
        ('news_analysis', 'analysis_date'),
        ('prophet_forecast', 'forecast_date'),
        ('ai_trade_decision', 'decision_date'),
        ('safety_filter_result', 'filter_date'),
        ('trade_execution_plan', 'execution_date'),
        ('trade_history', 'ordered_at')
    ]

    for table_name, date_col in tables:
        print(f"\n📊 Table: {table_name}")
        print("-" * 80)

        try:
            # Count total records
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cur.fetchone()[0]
            print(f"Total records: {total}")

            if total > 0:
                # Get date range
                if date_col in ['ordered_at', 'executed_at']:
                    cur.execute(f"""
                        SELECT
                            DATE(MIN({date_col})) as earliest,
                            DATE(MAX({date_col})) as latest,
                            COUNT(DISTINCT DATE({date_col})) as unique_dates
                        FROM {table_name}
                        WHERE {date_col} IS NOT NULL
                    """)
                else:
                    cur.execute(f"""
                        SELECT
                            MIN({date_col}) as earliest,
                            MAX({date_col}) as latest,
                            COUNT(DISTINCT {date_col}) as unique_dates
                        FROM {table_name}
                    """)

                result = cur.fetchone()
                if result and result[0]:
                    print(f"Date range: {result[0]} ~ {result[1]}")
                    print(f"Unique dates: {result[2]}")

                # Get today's data count
                today = date.today()
                if date_col in ['ordered_at', 'executed_at']:
                    cur.execute(f"""
                        SELECT COUNT(*)
                        FROM {table_name}
                        WHERE DATE({date_col}) = %s
                    """, (today,))
                else:
                    cur.execute(f"""
                        SELECT COUNT(*)
                        FROM {table_name}
                        WHERE {date_col} = %s
                    """, (today,))

                today_count = cur.fetchone()[0]
                print(f"Today's records ({today}): {today_count}")

                # Show sample data for today
                if today_count > 0:
                    print("\nSample today's data:")
                    if table_name == 'ai_trade_decision':
                        cur.execute(f"""
                            SELECT stock_code, decision, rank, reason
                            FROM {table_name}
                            WHERE {date_col} = %s
                            ORDER BY rank
                            LIMIT 5
                        """, (today,))
                    elif table_name == 'trade_execution_plan':
                        cur.execute(f"""
                            SELECT stock_code, trade_type, execution_status,
                                   planned_quantity, executed_at
                            FROM {table_name}
                            WHERE {date_col} = %s
                            LIMIT 5
                        """, (today,))
                    elif table_name == 'stock_filter_score':
                        cur.execute(f"""
                            SELECT stock_code, stock_name, scaler_score, is_selected
                            FROM {table_name}
                            WHERE {date_col} = %s
                            ORDER BY scaler_score DESC
                            LIMIT 5
                        """, (today,))
                    else:
                        cur.execute(f"""
                            SELECT * FROM {table_name}
                            WHERE {date_col} = %s
                            LIMIT 3
                        """, (today,))

                    for row in cur.fetchall():
                        print(f"  {row}")
            else:
                print("⚠️  No data in this table")

        except Exception as e:
            print(f"❌ Error checking {table_name}: {e}")

    # Check UNIQUE constraints
    print("\n" + "=" * 80)
    print("UNIQUE CONSTRAINTS CHECK")
    print("=" * 80)

    cur.execute("""
        SELECT
            tc.table_name,
            string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_type = 'UNIQUE'
          AND tc.table_schema = 'public'
          AND tc.table_name IN (
              'stock_filter_score', 'stock_financial', 'news_analysis',
              'prophet_forecast', 'ai_trade_decision', 'safety_filter_result',
              'trade_execution_plan'
          )
        GROUP BY tc.table_name, tc.constraint_name
        ORDER BY tc.table_name
    """)

    for row in cur.fetchall():
        table_name, columns = row
        print(f"\n📌 {table_name}: UNIQUE({columns})")

    cur.close()
    conn.close()

if __name__ == '__main__':
    check_table_data()
