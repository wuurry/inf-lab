import sqlite3
import os
import json
import csv
import xml.etree.ElementTree as ET

DB = 'js/cafe1.db'
OUTPUT_DIR = 'out'

# ==================== СИСТЕМА ЭКСПОРТА ДАННЫХ ====================

def ensure_output_dir():
    """Создать папку out если её нет"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Создана папка {OUTPUT_DIR}")

def get_table_structure(table_name):
    """Получить структуру таблицы и информацию о внешних ключах"""
    db = sqlite3.connect(DB)
    cursor = db.cursor()
    
    # Получаем информацию о колонках
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    # Получаем информацию о внешних ключах
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    foreign_keys = cursor.fetchall()
    
    db.close()
    
    return {
        'columns': [col[1] for col in columns],
        'foreign_keys': foreign_keys
    }

def get_related_data(foreign_key_info, main_row_id):
    """Получить связанные данные по внешнему ключу"""
    db = sqlite3.connect(DB)
    cursor = db.cursor()
    
    related_table = foreign_key_info[2]
    from_column = foreign_key_info[3]
    to_column = foreign_key_info[4]
    
    # Получаем все колонки связанной таблицы
    cursor.execute(f"PRAGMA table_info({related_table})")
    related_columns = [col[1] for col in cursor.fetchall()]
    
    # Получаем связанные данные
    cursor.execute(f"SELECT * FROM {related_table} WHERE {to_column} = ?", (main_row_id,))
    related_rows = cursor.fetchall()
    
    db.close()
    
    if not related_rows:
        return None
    
    # Преобразуем в список словарей
    result = []
    for row in related_rows:
        row_dict = {}
        for i, col_name in enumerate(related_columns):
            row_dict[col_name] = row[i]
        result.append(row_dict)
    
    return result[0] if len(result) == 1 else result

def export_table_data(table_name):
    """Экспортировать данные таблицы в различные форматы"""
    ensure_output_dir()
    
    db = sqlite3.connect(DB)
    cursor = db.cursor()
    
    # Получаем структуру таблицы
    structure = get_table_structure(table_name)
    columns = structure['columns']
    foreign_keys = structure['foreign_keys']
    
    # Получаем все данные из таблицы
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    # Преобразуем в список словарей с учетом связей
    data = []
    for row in rows:
        row_dict = {}
        
        # Основные данные
        for i, col_name in enumerate(columns):
            row_dict[col_name] = row[i]
        
        # Добавляем связанные данные
        for fk in foreign_keys:
            from_column = fk[3]
            related_table = fk[2]
            
            if from_column in row_dict:
                related_data = get_related_data(fk, row_dict[from_column])
                if related_data:
                    row_dict[related_table] = related_data
        
        data.append(row_dict)
    
    db.close()
    
    # Экспорт в различные форматы
    export_to_json(data, table_name)
    export_to_csv(data, table_name, columns, foreign_keys)
    export_to_xml(data, table_name)
    export_to_txt(data, table_name)
    
    print(f"Данные таблицы '{table_name}' экспортированы в папку {OUTPUT_DIR}/")
    return data

def export_to_json(data, table_name):
    """Экспорт в JSON"""
    filename = os.path.join(OUTPUT_DIR, f"{table_name}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

def export_to_csv(data, table_name, columns, foreign_keys):
    """Экспорт в CSV"""
    filename = os.path.join(OUTPUT_DIR, f"{table_name}.csv")
    
    # Собираем все возможные колонки для CSV
    all_columns = columns.copy()
    
    # Добавляем колонки из связанных таблиц
    for fk in foreign_keys:
        related_table = fk[2]
        all_columns.extend([f"{related_table}_{col}" for col in get_table_structure(related_table)['columns']])
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        
        for row in data:
            # Создаем плоскую структуру для CSV
            flat_row = {}
            
            # Основные данные
            for col in columns:
                flat_row[col] = row.get(col, '')
            
            # Данные из связанных таблиц
            for fk in foreign_keys:
                related_table = fk[2]
                if related_table in row:
                    related_data = row[related_table]
                    if isinstance(related_data, dict):
                        for key, value in related_data.items():
                            flat_row[f"{related_table}_{key}"] = value
                    elif isinstance(related_data, list):
                        flat_row[related_table] = '; '.join(str(item) for item in related_data)
            
            writer.writerow(flat_row)

def export_to_xml(data, table_name):
    """Экспорт в XML"""
    filename = os.path.join(OUTPUT_DIR, f"{table_name}.xml")
    
    root = ET.Element(table_name)
    
    for item in data:
        record = ET.SubElement(root, "record")
        dict_to_xml(item, record)
    
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)

def dict_to_xml(data, parent_element):
    """Рекурсивно преобразовать словарь в XML"""
    for key, value in data.items():
        if isinstance(value, dict):
            child = ET.SubElement(parent_element, key)
            dict_to_xml(value, child)
        elif isinstance(value, list):
            container = ET.SubElement(parent_element, key)
            for item in value:
                if isinstance(item, dict):
                    item_element = ET.SubElement(container, "item")
                    dict_to_xml(item, item_element)
                else:
                    ET.SubElement(container, "item").text = str(item)
        else:
            element = ET.SubElement(parent_element, key)
            element.text = str(value) if value is not None else ""

def export_to_txt(data, table_name):
    """Экспорт в текстовый формат"""
    filename = os.path.join(OUTPUT_DIR, f"{table_name}.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Данные таблицы: {table_name}\n")
        f.write("=" * 50 + "\n\n")
        
        for i, item in enumerate(data, 1):
            f.write(f"Запись #{i}:\n")
            f.write("-" * 30 + "\n")
            write_dict_to_txt(item, f, 1)
            f.write("\n")

def write_dict_to_txt(data, file, indent_level):
    """Рекурсивно записать словарь в текстовый файл"""
    indent = "  " * indent_level
    for key, value in data.items():
        if isinstance(value, dict):
            file.write(f"{indent}{key}:\n")
            write_dict_to_txt(value, file, indent_level + 1)
        elif isinstance(value, list):
            file.write(f"{indent}{key}:\n")
            for item in value:
                if isinstance(item, dict):
                    write_dict_to_txt(item, file, indent_level + 1)
                else:
                    file.write(f"{indent}  - {item}\n")
        else:
            file.write(f"{indent}{key}: {value}\n")

def get_available_tables():
    """Получить список всех таблиц в базе данных"""
    db = sqlite3.connect(DB)
    cursor = db.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [table[0] for table in cursor.fetchall()]
    
    db.close()
    return tables

def export_data_menu():
    """Меню экспорта данных"""
    ensure_output_dir()
    
    tables = get_available_tables()
    
    print("=== ЭКСПОРТ ДАННЫХ ИЗ БАЗЫ ДАННЫХ ===")
    print("Доступные таблицы:")
    for i, table in enumerate(tables, 1):
        print(f"{i}. {table}")
    
    try:
        choice = int(input("\nВыберите номер таблицы для экспорта: "))
        if 1 <= choice <= len(tables):
            selected_table = tables[choice - 1]
            print(f"\nЭкспорт данных из таблицы: {selected_table}")
            
            structure = get_table_structure(selected_table)
            print(f"Колонки: {', '.join(structure['columns'])}")
            
            if structure['foreign_keys']:
                print("Связи с другими таблицами:")
                for fk in structure['foreign_keys']:
                    print(f"  - {fk[3]} -> {fk[2]}.{fk[4]}")
            
            data = export_table_data(selected_table)
            
            print(f"\nЭкспортировано записей: {len(data)}")
            print(f"Файлы созданы в папке: {OUTPUT_DIR}/")
            print(f"   - {selected_table}.json")
            print(f"   - {selected_table}.csv") 
            print(f"   - {selected_table}.xml")
            print(f"   - {selected_table}.txt")
            
        else:
            print("Неверный выбор!")
    except ValueError:
        print("Ошибка: введите число!")
    except Exception as e:
        print(f"Ошибка при экспорте: {e}")
    
    input("\nНажмите Enter для выхода...")

# ==================== ОСНОВНАЯ СИСТЕМА КАФЕ ====================

def init_db():
    """Инициализация базы данных - только проверка соединения"""
    try:
        db = sqlite3.connect(DB)
        db.close()
        print("База данных подключена успешно")
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        raise

def update_table_status(table_number, status):
    """Обновить статус стола"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        c.execute("""
            UPDATE table_status 
            SET status = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE table_number = ?
        """, (status, table_number))
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"Ошибка при обновлении статуса стола: {e}")
        return False

def show_table_status():
    """Показать статусы всех столов"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        c.execute("""
            SELECT table_number, status, last_updated 
            FROM table_status 
            ORDER BY table_number
        """)
        
        tables = c.fetchall()
        print("\n=== СТАТУСЫ СТОЛОВ ===")
        print("№ Стола | Статус      | Последнее обновление")
        print("-" * 50)
        
        for table in tables:
            status_ru = {
                'free': 'Свободен',
                'occupied': 'Занят',
                'reserved': 'Бронь'
            }.get(table[1], table[1])
            
            print(f"{table[0]:<8} | {status_ru:<11} | {table[2]}")
        
        db.close()
    except Exception as e:
        print(f"Ошибка при получении статусов столов: {e}")

def change_table_status():
    """Изменить статус стола"""
    try:
        show_table_status()
        table_number = int(input("\nВведите номер стола: "))
        if table_number < 1 or table_number > 20:
            print("Ошибка: номер стола должен быть от 1 до 20!")
            input("Нажмите Enter для выхода...")
            return
            
        print("\nДоступные статусы:")
        print("1. free - Свободен")
        print("2. occupied - Занят")
        print("3. reserved - Бронь")
        
        status_choice = input("Выберите статус (1-3): ")
        status_map = {'1': 'free', '2': 'occupied', '3': 'reserved'}
        
        if status_choice not in status_map:
            print("Неверный выбор статуса!")
            input("Нажмите Enter для выхода...")
            return
        
        new_status = status_map[status_choice]
        if update_table_status(table_number, new_status):
            status_ru = {'free': 'Свободен', 'occupied': 'Занят', 'reserved': 'Бронь'}[new_status]
            print(f"Статус стола #{table_number} изменен на '{status_ru}'")
        else:
            print("Ошибка при изменении статуса стола")
            
    except ValueError:
        print("Ошибка: номер стола должен быть числом!")
    except Exception as e:
        print(f"Ошибка при изменении статуса стола: {e}")
    input("Нажмите Enter для выхода...")

def showMenu():
    """Показать меню"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        c.execute("SELECT id, title, price FROM menu ORDER BY id")
        items = c.fetchall()
        print("\n=== МЕНЮ КАФЕ ===")
        print("ID | Название            | Цена")
        print("-" * 40)
        for row in items:
            print(f"{row[0]:<2} | {row[1]:<20} | {row[2]} руб.")
        db.close()
    except Exception as e:
        print(f"Ошибка при получении меню: {e}")
    input("\nНажмите Enter для выхода...")

def createDish():
    """Добавить блюдо в меню"""
    try:
        title = input("Введите название блюда: ").strip()
        if not title:
            print("Название не может быть пустым!")
            input("Нажмите Enter для выхода...")
            return
            
        price = int(input("Введите цену: "))
        if price <= 0:
            print("Цена должна быть положительным числом!")
            input("Нажмите Enter для выхода...")
            return
            
        db = sqlite3.connect(DB)
        c = db.cursor()
        c.execute("INSERT INTO menu (title, price) VALUES (?, ?)", (title, price))
        db.commit()
        db.close()
        print(f"Блюдо '{title}' успешно добавлено в меню!")
    except ValueError:
        print("Ошибка: цена должна быть числом!")
    except Exception as e:
        print(f"Ошибка при добавлении блюда: {e}")
    input("Нажмите Enter для выхода...")

def deleteDish():
    """Удалить блюдо из меню"""
    try:
        showMenu()
        dish_id = int(input("\nВведите ID блюда для удаления: "))
        
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("SELECT title FROM menu WHERE id = ?", (dish_id,))
        dish = c.fetchone()
        if not dish:
            print("Блюдо с таким ID не найдено!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
        
        c.execute("""
            SELECT oi.id FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.menu_id = ? AND o.status = 'active'
        """, (dish_id,))
        
        if c.fetchone():
            print("Нельзя удалить блюдо, которое есть в активных заказах!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
        
        c.execute("DELETE FROM menu WHERE id = ?", (dish_id,))
        db.commit()
        db.close()
        print(f"Блюдо '{dish[0]}' удалено из меню!")
        
    except ValueError:
        print("Ошибка: ID должен быть числом!")
    except Exception as e:
        print(f"Ошибка при удалении блюда: {e}")
    input("Нажмите Enter для выхода...")

def createOrder():
    """Создать новый заказ"""
    try:
        show_table_status()
        
        table_number = int(input("\nВведите номер стола для заказа: "))
        if table_number < 1 or table_number > 20:
            print("Ошибка: номер стола должен быть от 1 до 20!")
            input("Нажмите Enter для выхода...")
            return None
            
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("SELECT status FROM table_status WHERE table_number = ?", (table_number,))
        table_status_result = c.fetchone()
        
        if not table_status_result:
            print(f"Ошибка: стол #{table_number} не существует!")
            db.close()
            input("Нажмите Enter для выхода...")
            return None
            
        if table_status_result[0] != 'free':
            print(f"Ошибка: стол #{table_number} уже занят или забронирован!")
            db.close()
            input("Нажмите Enter для выхода...")
            return None
        
        c.execute("INSERT INTO orders (table_number) VALUES (?)", (table_number,))
        order_id = c.lastrowid
        
        c.execute("UPDATE table_status SET status = 'occupied', last_updated = CURRENT_TIMESTAMP WHERE table_number = ?", (table_number,))
        
        db.commit()
        db.close()
        print(f"Заказ #{order_id} для стола {table_number} создан!")
        print("Статус стола автоматически изменен на 'Занят'")
        
        add_dishes_to_new_order(order_id)
        
        return order_id
        
    except ValueError:
        print("Ошибка: номер стола должен быть числом!")
        input("Нажмите Enter для выхода...")
        return None
    except Exception as e:
        print(f"Ошибка при создании заказа: {e}")
        input("Нажмите Enter для выхода...")
        return None

def add_dishes_to_new_order(order_id):
    """Добавить блюда в новый заказ"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"=== ДОБАВЛЕНИЕ БЛЮД В ЗАКАЗ #{order_id} ===")
            
            c.execute("""
                SELECT m.title, oi.quantity, m.price, oi.quantity * m.price as total
                FROM order_items oi
                JOIN menu m ON oi.menu_id = m.id
                WHERE oi.order_id = ?
            """, (order_id,))
            
            items = c.fetchall()
            if items:
                print("\nТекущие позиции в заказе:")
                total_sum = 0
                for item in items:
                    print(f"  - {item[0]} x{item[1]} = {item[3]} руб.")
                    total_sum += item[3]
                print(f"Общая сумма: {total_sum} руб.")
            else:
                print("\nВ заказе пока нет позиций")
            
            print("\n1. Добавить блюдо")
            print("2. Закончить и выйти")
            
            choice = input("\nВыберите действие: ")
            
            if choice == '1':
                c.execute("SELECT id, title, price FROM menu ORDER BY id")
                items = c.fetchall()
                print("\n=== МЕНЮ ===")
                print("ID | Название            | Цена")
                print("-" * 40)
                for row in items:
                    print(f"{row[0]:<2} | {row[1]:<20} | {row[2]} руб.")
                
                try:
                    dish_id = int(input("\nВведите ID блюда: "))
                    quantity = int(input("Введите количество: "))
                    
                    if quantity <= 0:
                        print("Количество должно быть положительным числом!")
                        input("Нажмите Enter для продолжения...")
                        continue
                    
                    c.execute("SELECT title FROM menu WHERE id = ?", (dish_id,))
                    dish = c.fetchone()
                    
                    if not dish:
                        print("Ошибка: блюдо не найдено!")
                        input("Нажмите Enter для продолжения...")
                        continue
                    
                    c.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)", 
                             (order_id, dish_id, quantity))
                    
                    db.commit()
                    print(f"Блюдо '{dish[0]}' добавлено в заказ!")
                    input("Нажмите Enter для продолжения...")
                    
                except ValueError:
                    print("Ошибка: ID и количество должны быть числами!")
                    input("Нажмите Enter для продолжения...")
                    
            elif choice == '2':
                break
            else:
                print("Неверный выбор!")
                input("Нажмите Enter для продолжения...")
        
        db.close()
        
    except Exception as e:
        print(f"Ошибка при добавлении блюд: {e}")
        input("Нажмите Enter для выхода...")

def addDishToOrder():
    """Добавить блюдо в существующий заказ"""
    try:
        showActiveOrders()
        
        order_id = int(input("\nВведите ID заказа: "))
        dish_id = int(input("Введите ID блюда: "))
        quantity = int(input("Введите количество: "))
        
        if quantity <= 0:
            print("Количество должно быть положительным числом!")
            input("Нажмите Enter для выхода...")
            return
            
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("SELECT id, status FROM orders WHERE id = ?", (order_id,))
        order = c.fetchone()
        if not order:
            print("Ошибка: заказ не найден!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
            
        if order[1] != 'active':
            print("Ошибка: нельзя добавить блюдо в завершенный заказ!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
            
        c.execute("SELECT title FROM menu WHERE id = ?", (dish_id,))
        dish = c.fetchone()
        if not dish:
            print("Ошибка: блюдо не найдено!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
        
        c.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)", 
                 (order_id, dish_id, quantity))
        
        db.commit()
        db.close()
        print(f"Блюдо '{dish[0]}' успешно добавлено в заказ!")
        
    except ValueError:
        print("Ошибка: все значения должны быть числами!")
    except Exception as e:
        print(f"Ошибка при добавлении блюда в заказ: {e}")
    input("Нажмите Enter для выхода...")

def removeDishFromOrder():
    """Удалить блюдо из заказа"""
    try:
        order_id = int(input("Введите ID заказа: "))
        dish_id = int(input("Введите ID блюда для удаления: "))
        
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("""SELECT m.title FROM order_items oi 
                     JOIN menu m ON oi.menu_id = m.id 
                     WHERE oi.order_id = ? AND oi.menu_id = ?""", 
                 (order_id, dish_id))
        dish = c.fetchone()
        
        if not dish:
            print("Ошибка: блюдо не найдено в заказе!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
        
        c.execute("DELETE FROM order_items WHERE order_id = ? AND menu_id = ?", 
                 (order_id, dish_id))
        db.commit()
        db.close()
        print(f"Блюдо '{dish[0]}' удалено из заказа!")
        
    except ValueError:
        print("Ошибка: ID должны быть числами!")
    except Exception as e:
        print(f"Ошибка при удалении блюда из заказа: {e}")
    input("Нажмите Enter для выхода...")

def showActiveOrders():
    """Показать активные заказы"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("""
            SELECT o.id, o.table_number, o.order_time, o.status
            FROM orders o 
            WHERE o.status = 'active'
            ORDER BY o.order_time DESC
        """)
        
        orders = c.fetchall()
        
        if not orders:
            print("Активных заказов нет.")
            db.close()
            return
        
        print("\n=== АКТИВНЫЕ ЗАКАЗЫ ===")
        for order in orders:
            print(f"\nЗаказ #{order[0]} | Стол: {order[1]} | Время: {order[2]} | Статус: {order[3]}")
            
            c.execute("""
                SELECT m.title, m.price, oi.quantity
                FROM order_items oi
                JOIN menu m ON oi.menu_id = m.id
                WHERE oi.order_id = ?
            """, (order[0],))
            
            items = c.fetchall()
            total = 0
            if items:
                for item in items:
                    item_total = item[1] * item[2]
                    total += item_total
                    print(f"  - {item[0]} x{item[2]} = {item_total} руб.")
            else:
                print("  (нет позиций)")
            
            print(f"  ИТОГО: {total} руб.")
        
        db.close()
    except Exception as e:
        print(f"Ошибка при получении активных заказов: {e}")

def changeOrderStatus():
    """Изменить статус заказа"""
    try:
        showActiveOrders()
        order_id = int(input("\nВведите ID заказа для изменения статуса: "))
        
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        c.execute("SELECT table_number FROM orders WHERE id = ?", (order_id,))
        order = c.fetchone()
        if not order:
            print("Заказ не найден!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
            
        table_number = order[0]
        
        print("\nДоступные статусы:")
        print("1. active - активный")
        print("2. completed - завершен")
        print("3. cancelled - отменен")
        
        status_choice = input("Выберите статус (1-3): ")
        status_map = {'1': 'active', '2': 'completed', '3': 'cancelled'}
        
        if status_choice not in status_map:
            print("Неверный выбор статуса!")
            db.close()
            input("Нажмите Enter для выхода...")
            return
            
        new_status = status_map[status_choice]
        c.execute("UPDATE orders SET status = ? WHERE id = ?", 
                 (new_status, order_id))
        
        if new_status in ['completed', 'cancelled']:
            update_table_status(table_number, 'free')
            print(f"Стол #{table_number} освобожден")
        
        db.commit()
        db.close()
        print(f"Статус заказа #{order_id} изменен на '{new_status}'")
    except ValueError:
        print("Ошибка: ID должен быть числом!")
    except Exception as e:
        print(f"Ошибка при изменении статуса заказа: {e}")
    input("Нажмите Enter для выхода...")

def generateReports():
    """Генерация отчетов для владельца"""
    try:
        db = sqlite3.connect(DB)
        c = db.cursor()
        
        print("\n=== ОТЧЕТЫ ===")
        
        c.execute("""
            SELECT SUM(m.price * oi.quantity) 
            FROM order_items oi 
            JOIN menu m ON oi.menu_id = m.id 
            JOIN orders o ON oi.order_id = o.id 
            WHERE o.status = 'completed'
        """)
        total_revenue = c.fetchone()[0] or 0
        print(f"Общая выручка: {total_revenue} руб.")
        
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        completed_orders = c.fetchone()[0]
        print(f"Завершенных заказов: {completed_orders}")
        
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'active'")
        active_orders = c.fetchone()[0]
        print(f"Активных заказов: {active_orders}")
        
        c.execute("SELECT status, COUNT(*) FROM table_status GROUP BY status")
        table_statuses = c.fetchall()
        print("\nСтатусы столов:")
        for status, count in table_statuses:
            status_ru = {'free': 'Свободны', 'occupied': 'Заняты', 'reserved': 'Бронь'}.get(status, status)
            print(f"- {status_ru}: {count} столов")
        
        print("\nСамые популярные блюда:")
        c.execute("""
            SELECT m.title, SUM(oi.quantity) as total_quantity
            FROM order_items oi 
            JOIN menu m ON oi.menu_id = m.id 
            GROUP BY m.id 
            ORDER BY total_quantity DESC 
            LIMIT 5
        """)
        popular_dishes = c.fetchall()
        for i, dish in enumerate(popular_dishes, 1):
            print(f"{i}. {dish[0]} - {dish[1]} порций")
        
        db.close()
    except Exception as e:
        print(f"Ошибка при генерации отчетов: {e}")
    input("\nНажмите Enter для выхода...")

# Меню для разных ролей
def waiterMenu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== МЕНЮ ОФИЦИАНТА ===")
        print("1. Показать меню")
        print("2. Создать новый заказ")
        print("3. Добавить блюдо в заказ")
        print("4. Удалить блюдо из заказа")
        print("5. Показать активные заказы")
        print("6. Изменить статус заказа")
        print("7. Показать статусы столов")
        print("8. Изменить статус стола")
        print("9. Выход")      
        
        choice = input("Выберите действие: ")
        
        if choice == '1':
            showMenu()
        elif choice == '2':
            createOrder()
        elif choice == '3':
            addDishToOrder()
        elif choice == '4':
            removeDishFromOrder()
        elif choice == '5':
            showActiveOrders()
            input("Нажмите Enter для выхода...")
        elif choice == '6':
            changeOrderStatus()
        elif choice == '7':
            show_table_status()
        elif choice == '8':
            change_table_status()
        elif choice == '9':
            break
        else:
            print("Неверный выбор!")
            input("Нажмите Enter для продолжения...")

def kitchenBarMenu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== МЕНЮ КУХНИ/БАРА ===")
        print("1. Показать меню")
        print("2. Показать активные заказы")
        print("3. Изменить статус заказа")
        print("4. Показать статусы столов")
        print("5. Выход")
        
        choice = input("Выберите действие: ")
        
        if choice == '1':
            showMenu()
        elif choice == '2':
            showActiveOrders()
            input("Нажмите Enter для выхода...")
        elif choice == '3':
            changeOrderStatus()
        elif choice == '4':
            show_table_status()
        elif choice == '5':
            break
        else:
            print("Неверный выбор!")
            input("Нажмите Enter для продолжения...")

def adminMenu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== МЕНЮ АДМИНИСТРАТОРА ===")
        print("1. Показать меню")
        print("2. Добавить блюдо в меню")
        print("3. Удалить блюдо из меню")
        print("4. Создать новый заказ")
        print("5. Добавить блюдо в заказ")
        print("6. Удалить блюдо из заказа")
        print("7. Показать активные заказы")
        print("8. Изменить статус заказа")
        print("9. Показать статусы столов")
        print("10. Изменить статус стола")
        print("11. Экспорт данных таблицы")
        print("12. Выход")
        
        choice = input("Выберите действие: ")
        
        if choice == '1':
            showMenu()
        elif choice == '2':
            createDish()
        elif choice == '3':
            deleteDish()
        elif choice == '4':
            createOrder()
        elif choice == '5':
            addDishToOrder()
        elif choice == '6':
            removeDishFromOrder()
        elif choice == '7':
            showActiveOrders()
            input("Нажмите Enter для выхода...")
        elif choice == '8':
            changeOrderStatus()
        elif choice == '9':
            show_table_status()
        elif choice == '10':
            change_table_status()
        elif choice == '11':
            export_data_menu()
        elif choice == '12':
            break
        else:
            print("Неверный выбор!")
            input("Нажмите Enter для продолжения...")

def ownerMenu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("=== МЕНЮ ВЛАДЕЛЬЦА ===")
        print("1. Показать меню")
        print("2. Добавить блюдо в меню")
        print("3. Удалить блюдо из меню")
        print("4. Показать активные заказы")
        print("5. Изменить статус заказа")
        print("6. Показать статусы столов")
        print("7. Изменить статус стола")
        print("8. Просмотреть отчеты")
        print("9. Экспорт данных таблицы")
        print("10. Выход")
        
        choice = input("Выберите действие: ")
        
        if choice == '1':
            showMenu()
        elif choice == '2':
            createDish()
        elif choice == '3':
            deleteDish()
        elif choice == '4':
            showActiveOrders()
            input("Нажмите Enter для выхода...")
        elif choice == '5':
            changeOrderStatus()
        elif choice == '6':
            show_table_status()
        elif choice == '7':
            change_table_status()
        elif choice == '8':
            generateReports()
        elif choice == '9':
            export_data_menu()
        elif choice == '10':
            break
        else:
            print("Неверный выбор!")
            input("Нажмите Enter для продолжения...")