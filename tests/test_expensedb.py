import datetime
import unittest

from lemur.expensedb import Table, Database


class TestDatabaseAndTable(unittest.TestCase):
    def setUp(self):
        self.db = Database()

        self.db.expense.insert_expense(
            amount=100.0,
            description="Dinner",
            owed_to="Ken",
            owed_from="Lily",
            date_created=datetime.datetime(year=2024, month=3, day=6, hour=1, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=20.0,
            description="Rides at the park",
            owed_to="Lily",
            owed_from="Ken",
            date_created=datetime.datetime(year=2024, month=3, day=7, hour=1, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=50.0,
            description="Tour",
            owed_to="Ken",
            owed_from="Steve",
            date_created=datetime.datetime(year=2024, month=3, day=7, hour=12, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=25,
            description="Taxis",
            owed_to="Steve",
            owed_from="Mike",
            date_created=datetime.datetime(year=2024, month=3, day=7, hour=12, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=10.50,
            description="Taxis",
            owed_to="Steve",
            owed_from="Lily",
            date_created=datetime.datetime(year=2024, day=8, month=3, hour=12, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=15,
            description="Taxis",
            owed_to="Steve",
            owed_from="Lily",
            date_created=datetime.datetime(year=2024, month=3, day=7, hour=12, minute=1, second=1),
        )
        self.db.expense.insert_expense(
            amount=-20,
            description="Squared Up",
            owed_to="Steve",
            owed_from="Lily",
            date_created=datetime.datetime(year=2024, month=3, day=7, hour=12, minute=1, second=1),
        )

    def tearDown(self):
        self.db.conn.close()

    def test_insert_and_select(self):
        date_created_val = datetime.datetime(year=2023, month=12, day=5, hour=12, minute=30)
        self.db.expense.insert(
            amount=20.55,
            description="Lunch",
            owed_to="Alice",
            owed_from="Bob",
            date_created=date_created_val,
        )
        result = self.db.expense.select(amount=20.55)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["amount"], 20.55)
        self.assertEqual(result[0]["description"], "Lunch")
        self.assertEqual(result[0]["owed_to"], "Alice")
        self.assertEqual(result[0]["owed_from"], "Bob")
        self.assertEqual(result[0]["date_created"], date_created_val)

    def test_select_with_like_condition(self):
        result = self.db.expense.select("description", "amount", description__contains="the park")

        self.assertEqual(len(result), 1)

    def test_to_string(self):
        db_string = self.db.to_string()
        self.assertIn(
            """CREATE TABLE""",
            db_string,
        )

    def test_expense_summary(self):
        self.assertListEqual(
            self.db.expense.summary(),
            [
                {
                    "person1": "Ken",
                    "person2": "Lily",
                    "total_amount": 80.0,
                    "direction": "Lily owes Ken",
                },
                {
                    "person1": "Ken",
                    "person2": "Steve",
                    "total_amount": 50.0,
                    "direction": "Steve owes Ken",
                },
                {
                    "person1": "Lily",
                    "person2": "Steve",
                    "total_amount": 5.5,
                    "direction": "Lily owes Steve",
                },
                {
                    "person1": "Mike",
                    "person2": "Steve",
                    "total_amount": 25.0,
                    "direction": "Mike owes Steve",
                },
            ],
        )

    def test_history(self):
        self.assertListEqual(
            self.db.expense.get_history("Ken"),
            [
                {
                    "amount": 50.0,
                    "description": "Tour",
                    "owed_to": "Ken",
                    "owed_from": "Steve",
                    "date_created": datetime.datetime(2024, 3, 7, 12, 1, 1),
                },
                {
                    "amount": 20.0,
                    "description": "Rides at the park",
                    "owed_to": "Lily",
                    "owed_from": "Ken",
                    "date_created": datetime.datetime(2024, 3, 7, 1, 1, 1),
                },
                {
                    "amount": 100.0,
                    "description": "Dinner",
                    "owed_to": "Ken",
                    "owed_from": "Lily",
                    "date_created": datetime.datetime(2024, 3, 6, 1, 1, 1),
                },
            ],
        )

    def test_get_unique_names(self):
        names = self.db.expense.get_unique_names()
        self.assertEqual(set(names), {"Ken", "Lily", "Mike", "Steve"})


if __name__ == "__main__":
    unittest.main()
