import io
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# Register the adapter and converter
def adapt_datetime(dt):
    return dt.isoformat()


def convert_datetime(s):
    return datetime.fromisoformat(s.decode("utf-8"))


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)


class Table:
    def __init__(self, db: "Database", table_name: str, columns: Dict[str, str]) -> None:
        """
        Initialize a Table object.

        :param db: The Database object this table belongs to.
        :param table_name: The name of the table.
        :param columns: A dictionary mapping column names to their SQL data types.
        """
        self.db = db
        self.table_name = table_name
        self.columns = columns

    def create(self) -> None:
        """
        Create the table in the database.
        """
        columns_definition = ", ".join([f"{k} {v}" for k, v in self.columns.items()])
        self.db.cursor.execute(f"CREATE TABLE {self.table_name} ({columns_definition})")

    def insert(self, **data) -> None:
        """
        Insert a row into the table.

        :param data: Column-value pairs to insert.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        self.db.cursor.execute(sql, list(data.values()))

    def delete(self, **where) -> None:
        """
        Delete rows from the table.

        :param where: Conditions for the WHERE clause.
        """
        where_clause = ""
        values = []

        if where:
            conditions = []
            for k, v in where.items():
                conditions.append(f"{k} = ?")
                values.append(v)

            where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"DELETE FROM {self.table_name} {where_clause}"
        self.db.cursor.execute(sql, values)

    def select(self, *columns: str, **where) -> List[Dict[str, Any]]:
        """
        Select rows from the table.

        :param columns: Columns to select. If none are provided, select all columns.
        :param where: Conditions for the WHERE clause.
        :return: A list of dictionaries representing the rows.
        """
        if not columns:
            columns = self.columns.keys()

        where_clause = ""
        values = []

        if where:
            conditions = []
            for k, v in where.items():
                if k.endswith("__contains"):
                    column_name = k.removesuffix("__contains")
                    conditions.append(f"{column_name} LIKE ?")
                    values.append(f"%{v}%")
                elif k.endswith("__gt"):
                    column_name = k.removesuffix("__gt")
                    conditions.append(f"{column_name} > ?")
                    values.append(v)
                elif k.endswith("__gte"):
                    column_name = k.removesuffix("__gte")
                    conditions.append(f"{column_name} >= ?")
                    values.append(v)
                elif k.endswith("__lt"):
                    column_name = k.removesuffix("__lt")
                    conditions.append(f"{column_name} < ?")
                    values.append(v)
                elif k.endswith("__lte"):
                    column_name = k.removesuffix("__lte")
                    conditions.append(f"{column_name} <= ?")
                    values.append(v)
                else:
                    conditions.append(f"{k} = ?")
                    values.append(v)

            where_clause = "WHERE " + " AND ".join(conditions)

        sql = f"SELECT {', '.join(columns)} FROM {self.table_name} {where_clause}"
        self.db.cursor.execute(sql, values)
        return [dict(row) for row in self.db.cursor.fetchall()]


class ExpenseTable(Table):
    def __init__(self, db: "Database") -> None:
        super().__init__(
            db,
            "expense",
            {
                "id": "INTEGER PRIMARY KEY",
                "amount": "REAL",
                "description": "TEXT",
                "owed_to": "TEXT",
                "owed_from": "TEXT",
                "date_created": "DATETIME",
            },
        )

    def summary(self):
        self.db.cursor.execute(
            f"""
            WITH DebtSummary AS (
                SELECT 
                    CASE 
                        WHEN owed_to < owed_from THEN owed_to 
                        ELSE owed_from 
                    END AS person1,
                    CASE 
                        WHEN owed_to < owed_from THEN owed_from 
                        ELSE owed_to 
                    END AS person2,
                    SUM(
                        CASE 
                            WHEN owed_to < owed_from THEN amount 
                            ELSE -amount 
                        END
                    ) AS net_amount
                FROM 
                    {self.table_name}
                GROUP BY 
                    person1, person2
            )
            SELECT 
                person1,
                person2,
                ABS(net_amount) AS total_amount,
                CASE
                    WHEN net_amount > 0 THEN person2 || ' owes ' || person1
                    ELSE person1 || ' owes ' || person2
                END AS direction
            FROM 
                DebtSummary
            WHERE 
                net_amount <> 0;
            """
        )

        return [dict(row) for row in self.db.cursor.fetchall()]

    def get_history(self, person):
        self.db.cursor.execute(
            f"""
            SELECT 
                amount,
                description,
                owed_to,
                owed_from,
                date_created
            FROM 
                {self.table_name}
            WHERE 
                owed_to = ? OR owed_from = ?
            ORDER BY 
                date_created DESC;
            """,
            (person, person),
        )

        return [dict(row) for row in self.db.cursor.fetchall()]

    def insert_expense(self, amount, description, owed_to, owed_from, date_created=None):
        self.insert(
            amount=amount,
            description=description,
            owed_to=owed_to,
            owed_from=owed_from,
            date_created=date_created or datetime.now(timezone.utc),
        )

    def get_unique_names(self):
        self.db.cursor.execute(
            f"""
            SELECT DISTINCT owed_to
            FROM {self.table_name}
            UNION
            SELECT DISTINCT owed_from
            FROM {self.table_name};
            """
        )
        return [row["owed_to"] for row in self.db.cursor.fetchall()]


class Database:
    def __init__(self, existing_db: Optional[str] = None) -> None:
        """
        Initialize a Database object.

        :param existing_db: SQL script to initialize the database with existing data, if any.
        """
        self.conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        self.expense = ExpenseTable(self)

        if existing_db:
            self.conn.executescript(existing_db)
        else:
            self.expense.create()

    def to_string(self) -> str:
        """
        Dump the database to a string.

        :return: The SQL script representing the database.
        """
        string_io = io.StringIO()
        for line in self.conn.iterdump():
            string_io.write("%s\n" % line)
        return string_io.getvalue()
