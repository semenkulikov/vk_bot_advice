from server_manager import server_1
from database.models import create_models


def main():
    server_1.start()


if __name__ == '__main__':
    create_models()  # Создаем таблицы в БД
    main()
