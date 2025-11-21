import os
from functions import *

# Инициализация базы данных при запуске
init_db()

while True:
    os.system('clear')
    print("Авторизация")
    print("Выберете вашу роль:")
    print("1. Официант")
    print("2. Кухня/бар")
    print("3. Администратор")
    print("4. Владелец")
    print("5. Выход")
    
    try:
        enter = int(input("Ваш выбор _: "))
        if enter == 1:
            waiterMenu() 
        elif enter == 2:
            kitchenBarMenu() 
        elif enter == 3:
            adminMenu() 
        elif enter == 4:
            ownerMenu()
        elif enter == 5:
            print("Выход из программы....")
            break
        else:
            print("Неверный выбор! Нажмите Enter для продолжения...")
            input()
    except ValueError:
        print("Ошибка: введите число от 1 до 5!")
        input("Нажмите Enter для продолжения....")