from server_manager import server_1
from database.models import create_models, create_time_tables, delete_time_tables
import schedule



def main():
    server_1.start()


if __name__ == '__main__':
    create_models()  # Создаем таблицы в БД
    # create_time_tables()

    schedule.every().monday.at("00:01").do(delete_time_tables)
    schedule.every().monday.at("00:01").do(create_time_tables)

    main()
