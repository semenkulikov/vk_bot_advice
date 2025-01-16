import datetime
import json
import threading

from database.models import User, Timetable
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger
from config_data.config import ADMIN_ID


def reservation_date_handler(event: VkBotEvent, vk_api_elem, online_advice=False) -> None:
    """
    Хендлер для бронирования определенного времени для консультации.
    :param online_advice: Онлайн прием
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)

    if user is None:
        app_logger.warning(f"Внимание! Запрос бронирования времени от неизвестного пользователя {user_id}")
        return

    if online_advice is True:
        app_logger.info(f"Запрос бронирования времени на онлайн прием от {user.full_name}")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Вы записываетесь на онлайн консультацию. "
                                          "Она проходит по четвергам и пятницам с 13:00 до 19:00.",
                                  random_id=get_random_id())

    else:
        app_logger.info(f"Запрос бронирования времени на личный прием от {user.full_name}")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Вы записываетесь на личную консультацию. "
                                          "Она проходит по понедельникам, вторникам и средам с 10:00 до 18:00.\n"
                                          "Перерыв на обед - с 12:00 до 14:00",
                                  random_id=get_random_id())
    # Получение текущей даты, получение существующих дат из БД.
    cur_datetime = datetime.datetime.now()
    existing_dates = list()
    for timetable_obj in Timetable.select().where(Timetable.date >= cur_datetime.date()):
        if timetable_obj.date == cur_datetime.date():
            if timetable_obj.start_time.hour >= cur_datetime.time().hour:
                if (online_advice is False and timetable_obj.date.weekday() in (0, 1, 2) or
                        online_advice is True and timetable_obj.date.weekday() in (3, 4)):
                    existing_dates.append(timetable_obj.date)
        else:
            if (online_advice is False and timetable_obj.date.weekday() in (0, 1, 2) or
                    online_advice is True and timetable_obj.date.weekday() in (3, 4)):
                existing_dates.append(timetable_obj.date)
    existing_dates = sorted(list(set(existing_dates)))
    # Генерирует клавиатуру с выбором существующих дат
    if len(existing_dates) > 8:
        keyboard = {
            "inline": True,
            "buttons": []
        }
        for i, date_str in enumerate(existing_dates):
            if i % 2 == 0:
                keyboard["buttons"].append([])
            keyboard["buttons"][i // 2].append({
                "action": {
                    "type": "text",
                    "label": f"{str(date_str)}"
                },
                "color": "primary"
            })
    else:
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
                              message="Выберите дату:",
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
    cur_time = datetime.datetime.now()
    free_times = []
    for timetable in Timetable.select().where(Timetable.date == date_reserved,
                                              Timetable.is_booked == False,
                                              ):
        if timetable.date == cur_time.date():
            if timetable.start_time.hour >= cur_time.time().hour:
                free_times.append(f"{timetable.start_time.strftime("%H:%M")} - {timetable.end_time.strftime("%H:%M")}")
        else:
            free_times.append(f"{timetable.start_time.strftime("%H:%M")} - {timetable.end_time.strftime("%H:%M")}")
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
        for i, time_str in enumerate(free_times[:10]):
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
                                  message="Выберите время:",
                                  random_id=get_random_id(),
                                  keyboard=json.dumps(keyboard))
        keyboard = {
            "inline": True,
            "buttons": []
        }
        for i, time_str in enumerate(free_times[10:]):
            if i % 2 == 0:
                keyboard["buttons"].append([])
            keyboard["buttons"][i // 2].append({
                "action": {
                    "type": "text",
                    "label": f"({day}) {time_str}"
                },
                "color": "primary"
            })
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="ᅠ",
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
    if user is None:
        app_logger.warning(f"Внимание! Запрос бронирования консультации от неизвестного пользователя {user_id}")
        return
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


    # Если профиль пользователя не содержит телефон, или ему меньше 21 года, то блокируем
    if user.phone is None:
        app_logger.warning(f"Внимание! Запрос бронирования консультации от {user.full_name} "
                           f"на {datetime_reserved} отклонен: нет телефона")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Пожалуйста, укажите ваш номер телефона для того, чтобы мы могли выслать напоминание о времени вашей записи!\n"
                                          "Напишите ваш номер телефона в формате: +79991234567",
                                  random_id=get_random_id())
        return
    elif user.birthday is None:
        app_logger.warning(f"Внимание! Запрос бронирования консультации от {user.full_name} "
                           f"на {datetime_reserved} отклонен: не указан день рождения")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Бронирование не удалось: не указан день рождения!\n"
                                          "Напишите ваш день рождения в формате: 12.13.1415 (день, месяц, год)",
                                  random_id=get_random_id())
        return
    user_birthday_list = [int(elem) for elem in user.birthday.split(".")]
    user_birthday = datetime.date(year=user_birthday_list[2], month=user_birthday_list[1],
                                  day=user_birthday_list[0])
    if (datetime.datetime.now().date() - user_birthday).days <= 7665:
        app_logger.warning(f"Внимание! Запрос бронирования консультации от {user.full_name} "
                           f"на {datetime_reserved} отклонен: менее 21 года")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="Бронирование не удалось: вы должны быть старше 21 года!",
                                  random_id=get_random_id())
        return
    # Присвоение найденному Timetable объекту user_id и изменение поля is_booked
    if cur_t is not None:
        cur_t.user_id = user.id
        cur_t.is_booked = True
        cur_t.save()
        app_logger.info(f"Бронирование консультации успешно завершено от {user.full_name} на {cur_t.date}")
        # Отправка уведомления пользователю
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Вы записаны на консультацию!\n"
                                          f"Ваше время: {start_time} - {end_time}\n"
                                          f"Дата: {cur_t.date}\n",
                                  random_id=get_random_id())

        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Мы отправим вам напоминание о времени "
                                          f"вашей записи за 2 часа до начала приема!",
                                  random_id=get_random_id())

        # Запуск напоминания о консультации за 2 часа до начала консультации
        send_notification(cur_t.id, vk_api_elem)
        # Отправка уведомления администратору о бронировании
        app_logger.info(f"Отправка уведомления администратору о новом бронировании консультации")
        vk_api_elem.messages.send(peer_id=ADMIN_ID,
                                  message=f"Новое бронирование консультации:\n"
                                          f"Пользователь: {user.full_name}\n"
                                          f"Номер телефона: {user.phone}\n"
                                          f"Дата рождения: {user.birthday} (больше 21)\n"
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
    consultation_datetime = datetime.datetime.combine(timetable.date, timetable.start_time)
    cur_datetime = datetime.datetime.now()

    # Вычисление точной даты: за день до приема до начала консультации previous_day вида 2025-10-01
    previous_day = timetable.date - datetime.timedelta(days=1)
    notification_datetime_previous_day = datetime.datetime.combine(previous_day, datetime.time(hour=9, minute=0))
    notification_datetime_current_day = datetime.datetime.combine(timetable.date, datetime.time(hour=9, minute=0))
    # Вычисление точной даты и времени: за два часа до начала консультации notification_datetime вида 2025-10-01 18:00
    notification_datetime_0 = (datetime.datetime.combine(timetable.date, timetable.start_time) -
                             datetime.timedelta(hours=2))


    # Создание асинхронных потоков таймеров.
    if consultation_datetime.time().hour >= 12:
        if datetime.datetime.now().date() < notification_datetime_previous_day.date():
            threading.Timer((notification_datetime_previous_day - cur_datetime).total_seconds(),
                            send_notification_message,
                            args=(user, vk_api_elem, consultation_datetime)).start()
            app_logger.info(f"Запланировано отправление уведомления {user.full_name} на "
                            f"{notification_datetime_previous_day}")

        threading.Timer((notification_datetime_current_day - cur_datetime).total_seconds(),
                        send_notification_message,
                        args=(user, vk_api_elem, consultation_datetime)).start()
        app_logger.info(f"Запланировано отправление уведомления {user.full_name} на "
                        f"{notification_datetime_current_day}")
    if notification_datetime_0 != notification_datetime_current_day:
        threading.Timer((notification_datetime_0 - cur_datetime).total_seconds(),
                        send_notification_message,
                        args=(user, vk_api_elem, consultation_datetime)).start()
        app_logger.info(f"Запланировано отправление уведомления {user.full_name} на "
                        f"{notification_datetime_0}")


def send_notification_message(user: User, vk_api_elem, consultation_datetime):
    """ Функция для отправки уведомления пользователю
    :param vk_api_elem: VkApiMethod
    :param user: объект пользователя
    :param consultation_datetime: время консультации
    """
    app_logger.info(f"Отправка уведомления пользователю {user.full_name}")
    vk_api_elem.messages.send(peer_id=user.user_id,
                              message=f"Напоминание!\nУ вас есть консультация на {consultation_datetime}.",
                              random_id=get_random_id())
