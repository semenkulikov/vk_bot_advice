import datetime
import json
import threading
import time

from database.models import User, Timetable
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger
from config import ADMIN_ID
import schedule


def reservation_date_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для бронирования определенного времени для консультации.
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)
    app_logger.info(f"Запрос бронирования времени от {user.full_name}")
    if user is None:
        app_logger.warning(f"Внимание! Запрос бронирования времени от неизвестного пользователя {user_id}")
        return

    # Получение текущей даты, получение существующих дат из БД.
    cur_datetime = datetime.datetime.now()
    existing_dates = sorted(list(set([t.date for t in Timetable.select().where(Timetable.date >= cur_datetime.date())])))

    # Генерирует клавиатуру с выбором существующих дат
    keyboard = {
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": f"{str(date_str)}"
                    },
                    "color": "primary"
                }
            ] for date_str in existing_dates]
    }
    # Отправляет пользователю клавиатуру с выбором даты.
    app_logger.info(f"Отправка клавиатуры с датами для бронирования консультации {user.full_name}")
    vk_api_elem.messages.send(peer_id=user_id,
                              message="Выберите дату бронирования консультации:",
                              random_id=get_random_id(),
                              keyboard=json.dumps(keyboard))


def reservation_time_handler(event: VkBotEvent, vk_api_elem, date_reserved: str) -> None:
    """
    Хендлер для бронирования определенного времени в конкретную дату для консультации.
    :param date_reserved: дата бронирования
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)
    app_logger.info(f"Запрос бронирования времени от {user.full_name} на дату {date_reserved}")
    if user is None:
        app_logger.warning(f"Внимание! Запрос бронирования времени от неизвестного пользователя {user_id}")
        return

    # Получение свободных часов консультаций по дате из БД.
    free_times = [f"{timetable.start_time} - {timetable.end_time}"
                  for timetable in Timetable.select().where(Timetable.date == date_reserved,
                                                            Timetable.is_booked == False)]
    if not free_times:
        app_logger.warning(f"Внимание! Нет свободных часов для бронирования консультации на {date_reserved} от {user.full_name}")
        # Отправка уведомления пользователю
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Извините, но на {date_reserved} нет свободных часов для бронирования консультации.",
                                  random_id=get_random_id())
    else:
        # Генерирование клавиатуры с выбором существующих часов (по 2 кнопки в ряд)
        keyboard = {
            "inline": True,
            "buttons": []
        }
        day = date_reserved.split("-")[-1]
        for i, time_str in enumerate(free_times):
            if i % 2 == 0:
                keyboard["buttons"].append([])
            keyboard["buttons"][i // 2].append({
                "action": {
                    "type": "text",
                    "label": f"({day}) {time_str}"
                },
                "color": "primary"
            })
        # Отправление пользователю клавиатуры с выбором времени.
        app_logger.info(f"Отправка клавиатуры с временами для бронирования консультации {user.full_name}")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Выберите время бронирования консультации:",
                                  random_id=get_random_id(),
                                  keyboard=json.dumps(keyboard))


def reservation_handler(event: VkBotEvent, vk_api_elem, datetime_reserved: str) -> None:
    """
    Хендлер для бронирования консультации.
    :param datetime_reserved: дата бронирования вида (day) HH:MM - HH:MM
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)
    app_logger.info(f"Запрос бронирования консультации от {user.full_name} на дату {datetime_reserved}")

    # Извлечение дня, стартовой даты и конечной даты из поля datetime_reserved
    day, times = datetime_reserved.split(" ", maxsplit=1)
    start_time, end_time = times.split(" - ")
    day = day[1:-1]

    # Поиск и получение всех объектов Timetable с данными датами начала и конца.
    timetables = Timetable.select().where(Timetable.start_time == start_time,
                                         Timetable.end_time == end_time,
                                         Timetable.is_booked == False)
    cur_t = None
    for t in timetables:
        # Проверка, что день содержится в дате
        if str(t.date.day) in day:
            cur_t = t
            break

    # Присвоение найденному Timetable объекту user_id и изменение поля is_booked
    if cur_t is not None:
        cur_t.user_id = user.id
        cur_t.is_booked = True
        cur_t.save()
        app_logger.info(f"Бронирование консультации успешно завершено от {user.full_name} на {cur_t.date}")
        # Отправка уведомления пользователю
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Бронирование консультации успешно завершено.\n"
                                          f"Время: {start_time} - {end_time}\n"
                                          f"Дата: {cur_t.date}\n",
                                  random_id=get_random_id())

        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Вам будет отправлено напоминание за 2 часа до консультации. Ожидайте",
                                  random_id=get_random_id())

        # Запуск напоминания о консультации за 2 часа до начала консультации
        send_notification(cur_t.id, vk_api_elem)
        # Отправка уведомления администратору о бронировании
        app_logger.info(f"Отправка уведомления администратору о новом бронировании консультации")
        vk_api_elem.messages.send(peer_id=ADMIN_ID,
                                  message=f"Новое бронирование консультации:\n"
                                          f"Пользователь: {user.full_name}\n"
                                          f"Время: {start_time} - {end_time}\n"
                                          f"Дата: {cur_t.date}\n",
                                  random_id=get_random_id())


def send_notification(timetable_id: int, vk_api_elem):
    """ Функция для создания асинхронного потока для отправки уведомлений через библиотеку schedule
    :param vk_api_elem: VkApiMethod
    :param timetable_id: идентификатор бронирования объекта Timetable.
    """
    app_logger.info(f"Запуск асинхронного потока для отправки уведомления.")
    timetable = Timetable.get_by_id(timetable_id)
    user = User.get_by_id(timetable.user_id)

    # Вычисление точной даты и времени: за два часа до начала консультации notification_datetime вида 2025-10-01 18:00
    notification_datetime = (datetime.datetime.combine(timetable.date, timetable.start_time) -
                             datetime.timedelta(hours=2))

    # Создание асинхронного потока
    threading.Thread(target=lambda: send_notification_target(user, notification_datetime, vk_api_elem)).start()

def send_notification_target(user: User, notification_datetime: datetime, vk_api_elem):
    """ Функция для запланирования отправки уведомления через schedule
    :param vk_api_elem: VkApiMethod
    :param notification_datetime: точное время отправки уведомления.
    :param user: объект пользователя.
    """
    app_logger.info(f"Запланировано отправление уведомления {user.full_name} на {notification_datetime}")

    schedule.every().day.at(notification_datetime.strftime("%H:%M")).do(send_notification_message, user, vk_api_elem)

    # Ожидание завершения всех заданий в schedule
    while True:
        schedule.run_pending()
        time.sleep(1)

def send_notification_message(user: User, vk_api_elem):
    """ Функция для отправки уведомления пользователю
    :param vk_api_elem: VkApiMethod
    :param user: объект пользователя
    """
    app_logger.info(f"Отправка уведомления пользователю {user.full_name}")
    vk_api_elem.messages.send(peer_id=user.user_id,
                              message=f"Напоминание!\nУ вас есть консультация на {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}.",
                              random_id=get_random_id())