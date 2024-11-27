import os
from flask import Flask, render_template, request, redirect, url_for, flash
from database import Database, DateInterval
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'
database = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_db', methods=['GET', 'POST'])
def create_db():
    global database
    if request.method == 'POST':
        db_name = request.form['db_name']
        if db_name:
            database = Database(db_name)
            flash(f"Database '{db_name}' created!", "success")
            return redirect(url_for('index'))
        else:
            flash("Database name cannot be empty.", "error")
    return render_template('create_db.html')

@app.route('/manage_table', methods=['GET', 'POST'])
def manage_table():
    if request.method == 'POST':
        if not database:
            flash("Create a database first.", "error")
            return redirect(url_for('index'))

        table_name = request.form['table_name']
        schema_input = request.form['schema']

        if table_name and schema_input:
            try:
                schema = parse_schema(schema_input)
                database.create_table(table_name, schema)
                flash(f"Table '{table_name}' created!", "success")
                return redirect(url_for('manage_table'))
            except Exception as e:
                flash(str(e), "error")

    return render_template('manage_table.html', tables=database.tables if database else None)

@app.route('/view_table/<table_name>', methods=['GET', 'POST'])
def view_table(table_name):
    table = database.tables.get(table_name)
    if not table:
        flash(f"Table '{table_name}' does not exist.", "error")
        return redirect(url_for('manage_table'))

    if request.method == 'POST':
        row_data = request.form.getlist('row_data')
        if row_data:
            try:
                row_data = parse_row_data(row_data, table.schema)
                table.add_row(row_data)
                flash(f"Row added to '{table_name}'!", "success")
                return redirect(url_for('view_table', table_name=table_name))
            except Exception as e:
                flash(str(e), "error")  # Показати повідомлення про помилку валідації

    return render_template('view_table.html', table=table)

@app.route('/edit_row/<table_name>/<int:row_index>', methods=['GET', 'POST'])
def edit_row(table_name, row_index):
    table = database.tables.get(table_name)
    if not table or row_index >= len(table.rows):
        flash("Invalid table or row index.", "error")
        return redirect(url_for('manage_table'))

    if request.method == 'POST':
        row_data = request.form.getlist('row_data')
        if row_data:
            try:
                row_data = parse_row_data(row_data, table.schema)
                table.rows[row_index] = row_data  # Edit the row directly
                flash(f"Row in '{table_name}' updated!", "success")
                return redirect(url_for('view_table', table_name=table_name))
            except Exception as e:
                flash(str(e), "error")  # Показати повідомлення про помилку валідації

    return render_template('edit_row.html', table=table, row_index=row_index)

@app.route('/delete_row/<table_name>/<int:row_index>', methods=['POST'])
def delete_row(table_name, row_index):
    table = database.tables.get(table_name)
    if not table or row_index >= len(table.rows):
        flash("Invalid table or row index.", "error")
    else:
        table.rows.pop(row_index)  # Remove the row
        flash(f"Row in '{table_name}' deleted!", "success")

    return redirect(url_for('view_table', table_name=table_name))

@app.route('/save_db', methods=['POST'])
def save_db():
    if not database:
        flash("No database to save.", "error")
        return redirect(url_for('manage_table'))
    filename = request.form['filename']
    if filename:
        database.save_to_file(filename)
        flash(f"Database saved to '{filename}'!", "success")
    else:
        flash("Filename cannot be empty.", "error")
    return redirect(url_for('manage_table'))

@app.route('/load_db', methods=['POST'])
def load_db():
    global database
    filename = request.form['filename']
    if os.path.exists(filename):
        database = Database.load_from_file(filename)
        flash(f"Database loaded from '{filename}'!", "success")
    else:
        flash(f"File '{filename}' does not exist.", "error")
    return redirect(url_for('manage_table'))

@app.route('/tables/difference', methods=['GET', 'POST'])
def table_difference():
    if request.method == 'POST':
        table_name_1 = request.form['table_name_1']
        table_name_2 = request.form['table_name_2']
        table_1 = database.tables.get(table_name_1)
        table_2 = database.tables.get(table_name_2)

        if table_1 and table_2:
            try:
                diff_only_in_1, diff_only_in_2 = table_1.difference(table_2)
                return render_template('difference.html',
                                       table_name_1=table_name_1,
                                       table_name_2=table_name_2,
                                       diff_only_in_1=diff_only_in_1,
                                       diff_only_in_2=diff_only_in_2)
            except ValueError as e:
                flash(str(e), 'error')
        else:
            flash('One or both tables do not exist.', 'error')

    tables = database.tables.keys()
    return render_template('table_difference.html', tables=tables)

def parse_schema(schema_input):
    schema = []
    for field in schema_input.split(','):
        field_name, field_type = field.split(':')
        field_type = field_type.strip()
        if field_type == "int":
            schema.append((field_name.strip(), int))
        elif field_type == "real":
            schema.append((field_name.strip(), float))
        elif field_type == "char":
            schema.append((field_name.strip(), str))  # char as str
        elif field_type == "string":
            schema.append((field_name.strip(), str))
        elif field_type == "date":
            schema.append((field_name.strip(), date))
        elif field_type == "dateInvl":
            schema.append((field_name.strip(), DateInterval))
        else:
            raise Exception(f"Invalid type '{field_type}' for field '{field_name.strip()}'.")
    return schema

def parse_row_data(row_data, schema):
    if len(row_data) != len(schema):
        raise Exception("Row length does not match table schema.")

    parsed_data = []
    for (field_name, field_type), value in zip(schema, row_data):
        if field_type == str and len(value) > 1:  # Для char
            raise Exception(f"Invalid type for field '{field_name}'. Expected char, got string with length > 1.")

        if field_type == int:
            parsed_data.append(int(value))
        elif field_type == float:
            parsed_data.append(float(value))
        elif field_type == str:
            parsed_data.append(value)
        elif field_type == date:
            parsed_data.append(date.fromisoformat(value))  # Парсинг дати
        elif field_type == DateInterval:
            try:
                # Розділення рядка на два значення дати
                start_date_str, end_date_str = value.split(';')
                start_date = date.fromisoformat(start_date_str.strip())
                end_date = date.fromisoformat(end_date_str.strip())
                parsed_data.append(DateInterval(start_date, end_date))
            except ValueError as e:
                raise Exception(f"Invalid date format for DateInterval in field '{field_name}': {e}")
            except Exception as e:
                raise Exception(f"Error processing DateInterval for field '{field_name}': {e}")
        else:
            raise Exception(
                f"Invalid type for field '{field_name}'. Expected {field_type.__name__}, got {type(value).__name__}.")

    return parsed_data

if __name__ == '__main__':
    app.run(debug=True)
