import json
from datetime import date


class DateInterval:
    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date

    def to_dict(self):
        return {'start_date': self.start_date.isoformat(), 'end_date': self.end_date.isoformat()}

    def __repr__(self):
        return f"{self.start_date}; {self.end_date}"

    @classmethod
    def from_dict(cls, data):
        return cls(date.fromisoformat(data['start_date']), date.fromisoformat(data['end_date']))


class Table:
    def __init__(self, name, schema):
        self.name = name
        self.schema = schema
        self.rows = []

    def add_row(self, row_data):
        self.rows.append(row_data)

    # Метод для порівняння двох таблиць
    def difference(self, other_table):
        if self.schema != other_table.schema:
            raise ValueError("Tables have different schemas. Cannot compare.")

        # Знаходимо рядки, які є тільки в одній таблиці
        only_in_self = [row for row in self.rows if row not in other_table.rows]
        only_in_other = [row for row in other_table.rows if row not in self.rows]

        return only_in_self, only_in_other

    def _serialize_row(self, row):
        serialized_row = []
        for field, value in zip(self.schema, row):
            if isinstance(value, date):
                serialized_row.append(value.isoformat())  # Convert date to ISO format
            elif isinstance(value, DateInterval):
                serialized_row.append(
                    f"{value.start_date.isoformat()};{value.end_date.isoformat()}")  # Serialize DateInterval
            else:
                serialized_row.append(value)
        return serialized_row

    def get_schema(self):
        return self.schema

    def to_dict(self):
        return {
            'name': self.name,
            'schema': [(field_name, field_type.__name__) for field_name, field_type in self.schema],
            'rows': [self._serialize_row(row) for row in self.rows]
        }

    def _deserialize_row(self, row_data):
        deserialized_row = []
        for (field_name, field_type), value in zip(self.schema, row_data):
            if field_type == date:
                deserialized_row.append(date.fromisoformat(value))  # Deserialize date
            elif field_type == DateInterval:
                start_date, end_date = value.split(';')
                deserialized_row.append(DateInterval(date.fromisoformat(start_date.strip()), date.fromisoformat(end_date.strip())))  # Deserialize DateInterval
            else:
                deserialized_row.append(value)
        return deserialized_row

    @classmethod
    def from_dict(cls, data):
        schema = [(field_name, cls._map_type(field_type)) for field_name, field_type in data['schema']]
        table = cls(data['name'], schema)
        table.rows = [table._deserialize_row(row_data) for row_data in data['rows']]
        return table

    @staticmethod
    def _map_type(type_name):
        if type_name == 'int':
            return int
        elif type_name == 'float':
            return float
        elif type_name == 'str':
            return str
        elif type_name == 'date':
            return date
        elif type_name == 'DateInterval':
            return DateInterval
        else:
            raise Exception(f"Unknown type: {type_name}")


class Database:
    def __init__(self, name):
        self.name = name
        self.tables = {}

    def create_table(self, table_name, schema):
        if table_name in self.tables:
            raise Exception(f"Table '{table_name}' already exists.")
        self.tables[table_name] = Table(table_name, schema)

    def save_to_file(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            database = cls(data['name'])
            for table_data in data['tables']:
                database.tables[table_data['name']] = Table.from_dict(table_data)
            return database

    def to_dict(self):
        return {
            'name': self.name,
            'tables': [table.to_dict() for table in self.tables.values()]
        }
