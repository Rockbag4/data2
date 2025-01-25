from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
from sqlalchemy import create_engine, text
import os

app = Flask(__name__, template_folder='templates')#создаем flask-приложение, указываем папку с шаблонами
DATABASE_URI = ''#глобальная переменная для хранения uri базы данных

def create_database(db_name):
   #создает базу данных sqlite
    global DATABASE_URI
    DATABASE_URI = f'sqlite:///{db_name}.db'#формируем uri базы данных
    engine = create_engine(DATABASE_URI)#создаем движок базы данных
    return engine#возвращаем движок

def excel_to_db(file_path, engine):
    #читает excel файл и создает таблицы в бд
    with pd.ExcelFile(file_path) as xls:#используем менеджер контекста для автоматического закрытия файла
        for sheet_name in xls.sheet_names:#проходим по всем листам excel-файла
            df = pd.read_excel(xls, sheet_name=sheet_name)#читаем лист в pandas dataframe
            df.to_sql(sheet_name, engine, if_exists='replace', index=False)#записываем dataframe в таблицу sql, если есть - перезаписываем, без индексов

def get_tables(engine):
    #получает список таблиц из базы данных
    with engine.connect() as connection:
        result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()#выполняем sql запрос для получения имен таблиц
        tables = [row[0] for row in result]#формируем список имен таблиц
    return tables#возвращаем список

def get_table_data(engine, table_name):
    #получает данные из таблицы
    with engine.connect() as connection:
        result = connection.execute(text(f"SELECT * FROM `{table_name}`;")).fetchall()
        columns = connection.execute(text(f"PRAGMA table_info('{table_name}');")).fetchall()
        column_names = [col[1] for col in columns]
        # Преобразуем список кортежей в список списков
        data_list = [list(row) for row in result]
    return column_names, data_list#возвращаем имена столбцов и данные

@app.route('/', methods=['GET', 'POST'])
def index():
   #обрабатывает главную страницу, загрузку excel и создание бд
    if request.method == 'POST':#если форма отправлена методом post
        db_name = request.form['db_name']#получаем имя базы данных из формы
        excel_file = request.files['excel_file']#получаем excel-файл из формы

        if excel_file.filename == '':
            return render_template('index.html', error='файл не выбран')#если файл не выбран - сообщаем об ошибке

        if not excel_file.filename.lower().endswith(('.xls', '.xlsx')):
            return render_template('index.html', error='неправильный формат файла, выберите excel')#если неправильный формат файла - сообщаем об ошибке

        if not db_name:
            return render_template('index.html', error='название базы данных не может быть пустым')#если имя бд пустое - сообщаем об ошибке

        if os.path.exists(f'{db_name}.db'):
            return render_template('index.html', error='база данных с таким именем уже существует')#если бд существует - сообщаем об ошибке

        engine = create_database(db_name)#создаем базу данных
        excel_file_path = "temp.xlsx"#временный путь к файлу
        excel_file.save(excel_file_path)#сохраняем файл
        try:
            excel_to_db(excel_file_path, engine)#записываем данные из excel в базу данных
            os.remove(excel_file_path)#удаляем временный файл
            return redirect(url_for('tables'))#перенаправляем на страницу с таблицами
        except Exception as e:
            os.remove(excel_file_path)#удаляем временный файл в случае ошибки
            return render_template('index.html', error=f'ошибка при чтении файла: {str(e)}')#сообщаем об ошибке

    return render_template('index.html')#отрисовываем главную страницу

@app.route('/tables')
def tables():
    #отображает список таблиц в базе данных
    global DATABASE_URI
    if not DATABASE_URI:
        return 'база данных не создана', 404#если бд не создана - возвращаем ошибку
    engine = create_engine(DATABASE_URI)#создаем движок базы данных
    tables = get_tables(engine)#получаем список таблиц
    return render_template('tables.html', tables=tables)#отрисовываем страницу со списком таблиц

@app.route('/table/<table_name>')
def table(table_name):
    #отображает данные конкретной таблицы
    global DATABASE_URI
    if not DATABASE_URI:
        return 'база данных не создана', 404#если бд не создана - возвращаем ошибку
    engine = create_engine(DATABASE_URI)#создаем движок базы данных
    columns, data = get_table_data(engine, table_name)#получаем имена столбцов и данные таблицы
    return render_template('table_view.html', table_name=table_name, columns=columns, data=data)#отрисовываем страницу с данными таблицы

if __name__ == '__main__':
    app.run(debug=True)#запускаем приложение в режиме отладки
