from database.models import User, Timetable
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger
from config_data.config import BASE_DIR, ADMIN_ID, KEYBOARD
import os
import datetime
import json


start_text = """
Здравствуйте, {full_name}! Если вы хотите записаться на консультацию, пожалуйста выберите одну из двух зеленых кнопок, расположенных ниже.

Если вас интересует дополнительная информация — выберите кнопку «Частые вопросы», возможно там вы найдете ответ на свой вопрос.

ВАЖНО! Для записи на консультацию, вам должно быть не менее 21 года.
"""

def get_current_timetable_from_timetable_str(cur_user: User, timetable_str: str) -> Timetable:
    """
    Функция для извлечения данных из строкового представления объекта Timetable
    :param cur_user: объект пользователя
    :param timetable_str: строковое представление
    :return: Timetable объект
    """
    t_day, t_month = timetable_str.split(":")[0].split(".")
    t_date = datetime.date(year=datetime.date.today().year, month=int(t_month), day=int(t_day))
    t_hour_start, t_minute_start = timetable_str.split(":")[1][1:], timetable_str.split(":")[2].split(" ")[0]
    t_hour_end, t_minute_end = timetable_str.split(":")[2].split(" - ")[1], timetable_str.split(":")[3]
    t_time_start = datetime.time(int(t_hour_start), int(t_minute_start), 0)
    t_time_end = datetime.time(int(t_hour_end), int(t_minute_end), 0)
    # Получение объекта Timetable по данному дню, месяцу, времени начала и окончания
    for timetable_obj in Timetable.select().where(Timetable.user_id == cur_user, Timetable.is_booked == True):
        if (timetable_obj.date.day == t_date.day and timetable_obj.date.month == t_date.month
        and timetable_obj.start_time.hour == t_time_start.hour and
                timetable_obj.start_time.minute == t_time_start.minute
        and timetable_obj.end_time.hour == t_time_end.hour and timetable_obj.end_time.minute == t_time_end.minute):
            return timetable_obj
    return None


def start_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для обработки сообщений от пользователей.
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """

    user_id = event.object.message["from_id"]
    user_obj = vk_api_elem.users.get(user_id=user_id)[0]
    full_name = f"{user_obj['first_name']} {user_obj['last_name']}"
    address = user_obj.get("city", {}).get('title', None)
    phone = user_obj.get("contacts", None)
    birthday = user_obj.get("bdate", None)

    app_logger.info(f"Новое сообщение от {full_name}: {event.object.message["text"]}")
    # Проверка, существует ли такой пользователь в базе данных
    user = User.get_or_none(User.user_id == user_id)

    if user is not None:
        # Если есть, то приветствуем.
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=start_text.format(full_name=full_name),
                                  random_id=get_random_id(),
                                  keyboard=KEYBOARD)
    else:
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=start_text.format(full_name=full_name),
                                  random_id=get_random_id(),
                                  keyboard=KEYBOARD)
        # if phone is None:
        #     vk_api_elem.messages.send(peer_id=user_id,
        #                               message=f"Внимание! Не удалось получить номер телефона.\n"
        #                                       f"Напишите его отдельно в формате +79991234567, без номера телефона вы не "
        #                                       f"сможете записаться на консультацию!",
        #                               random_id=get_random_id(),
        #                               keyboard=KEYBOARD)
        # if birthday is None:
        #     vk_api_elem.messages.send(peer_id=user_id,
        #                               message=f"Внимание! Не удалось получить дату рождения.\n"
        #                                       f"Напишите ее отдельно в формате 12.13.1415 (день, месяц, год), иначе вы не "
        #                                       f"сможете записаться на консультацию!",
        #                               random_id=get_random_id(),
        #                               keyboard=KEYBOARD)
        user = User.create(user_id=user_id,
                          full_name=full_name,
                          phone=phone,
                          address=address,
                          birthday=birthday)

        app_logger.info(f"Новый пользователь {full_name} добавлен в базу.")


def often_questions_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для выдачи ответов на основные вопросы
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)
    app_logger.info(f"Запрос ответов на вопросы от {user.full_name}.")

    result_text = """
    1. Что можно с собой принести на прием? — Вы можете принести с собой одну фотографию человека, о котором хотите узнать.\n
    2. Сколько длиться прием? — Длительность сессии составляет около 20 минут.\n
    3. По какому адресу идет прием? — г. Магнитогорск, ул. Жукова, д. 17, отдельный вход рядом с подъездом №1.\n
    4. Я беременна, могу я прийти на прием? — Да, я работаю с белой магией, это безопасно для женщин в положении.\n
    5. Какова стоимость приема? — Вы оплачиваете мою работу, суммой на свое усмотрение.\n
    6. Могу ли я привести с собой на прием несовершеннолетнего ребенка? — Да, в вашем присутствии я могу посмотреть здоровье ребенка.\n
    7. Можете ли вы предсказать будущее? — Да, я могу увидеть основные линии развития жизни.\n
    8. Можете ли вы помочь избавиться от алкогольной или другой зависимости? — Да, в большинстве случаев результат положительный.
    """
    vk_api_elem.messages.send(peer_id=user_id,
                              message=f"Здесь собраны ответы на основные вопросы.\n{result_text}",
                              random_id=get_random_id(),
                              keyboard=KEYBOARD)


def add_birthday_handler(event: VkBotEvent, vk_api_elem, birthday) -> None:
    """
    Хендлер для добавления даты рождения пользователя
    :param birthday: дата рождения
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]
    user = User.get_or_none(User.user_id == user_id)

    app_logger.info(f"Запрос добавления даты рождения {birthday} от {user.full_name}.")
    user.birthday = birthday
    user.save()

    # Отправляем пользователю сообщение об успешном добавлении даты рождения

    vk_api_elem.messages.send(peer_id=user_id,
                              message="Данные сохранены. Пожалуйста, запишитесь повторно на консультацию.",
                              random_id=get_random_id(),
                              keyboard=KEYBOARD)

    user_birthday_list = [int(elem) for elem in user.birthday.split(".")]
    user_birthday = datetime.date(year=user_birthday_list[2], month=user_birthday_list[1],
                                  day=user_birthday_list[0])

    if (datetime.datetime.now().date() - user_birthday).days <= 7665:
        app_logger.warning(f"Внимание! Пользователь {user.full_name} слишком малой! Ему менее 21 года ({birthday})")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="ВАЖНО! Чтобы я могла записать вас на консультацию, "
                                          "ваш возраст должен быть не менее 21 года.",
                                  random_id=get_random_id(),
                                  keyboard=KEYBOARD)



def add_phone_handler(event: VkBotEvent, vk_api_elem, phone_number) -> None:
    """
    Хендлер для добавления номера телефона пользователя
    :param phone_number: номер телефона
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]
    user = User.get_or_none(User.user_id == user_id)

    app_logger.info(f"Запрос добавления номера телефона {phone_number} от {user.full_name}.")

    # Добавляем номер телефона в базу данных
    user.phone = phone_number
    user.save()

    # Отправляем пользователю сообщение об успешном добавлении номера телефона

    vk_api_elem.messages.send(peer_id=user_id,
                              message="Данные сохранены. Пожалуйста, запишитесь повторно на консультацию.",
                              random_id=get_random_id(),
                              keyboard=KEYBOARD)
keyboard = open(os.path.join(BASE_DIR, "keyboards/default.json"), "r", encoding="UTF-8").read()

def my_timetables_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для отображения информации по текущим записям пользователя.
    Бот выдает список текущих записей пользователя в виде кнопок.
    Нажав на запись, можно просмотреть - под сообщением будет кнопка удалить.
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]
    user: User = User.get_or_none(User.user_id == user_id)

    if not user:
        app_logger.warning(f"Пользователь с id {user_id} не найден в базе данных.")
        return

    # Получаем все записи Timetable пользователя
    timetables = Timetable.select().where(Timetable.user_id == user, Timetable.is_booked == True)

    if timetables.count() == 0:
        app_logger.info(f"Пользователь {user.full_name} не имеет текущих записей.")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="У вас нет текущих записей на консультации.",
                                  random_id=get_random_id(),
                                  keyboard=KEYBOARD)
        return

    # Формируем текст сообщения с кнопками удаления для каждой записи
    timetables_keyboard = {
            "inline": True,
            "buttons": []
        }

    timetables_str = [f"{elem.date.strftime("%d.%m")}: {elem.start_time.strftime("%H:%M")} - {elem.end_time.strftime("%H:%M")}"
                      for elem in timetables]
    for i, time_str in enumerate(timetables_str):
        if i % 2 == 0:
            timetables_keyboard["buttons"].append([])
        timetables_keyboard["buttons"][i // 2].append({
            "action": {
                "type": "text",
                "label": f"{str(time_str)}"
            },
            "color": "primary"
        })
    timetables_keyboard = json.dumps(timetables_keyboard)
    app_logger.info(f"Пользователь {user.full_name} запросил информацию о своих записях")
    vk_api_elem.messages.send(peer_id=user_id,
                              message="Ваши текущие записи на консультации:",
                              random_id=get_random_id(),
                              keyboard=timetables_keyboard)

def get_timetable_handler(event: VkBotEvent, vk_api_elem, timetable_str: str) -> None:
    """
     Хендлер для отображения записи на прием "
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :param timetable_str: информация о приеме вида %m.%d: %H:%M - %H:%M
    :return: None
    """
    user_id = event.object.message["from_id"]
    cur_user: User = User.get_or_none(User.user_id == user_id)

    cur_timetable_obj = get_current_timetable_from_timetable_str(cur_user, timetable_str)
    app_logger.info(f"Пользователь {cur_user.full_name} получил информацию о записи {timetable_str}")
    delete_keyboard = json.dumps({
        "inline": True,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "payload": "{\"button\": \"1\"}",
                        "label": f"Отменить запись {timetable_str}"
                    },
                    "color": "negative"
                }
            ],
    ]})
    vk_api_elem.messages.send(peer_id=user_id,
                              message=f"Информация о записи:\n"
                                      f"Дата: {cur_timetable_obj.date.strftime('%d.%m')}\n"
                                      f"Время: c {cur_timetable_obj.start_time.strftime('%H:%M')} до "
                                      f"{cur_timetable_obj.end_time.strftime('%H:%M')}",
                              random_id=get_random_id(),
                              keyboard=delete_keyboard)


def delete_timetable_handler(event: VkBotEvent, vk_api_elem, timetable_str: str) -> None:
    """
    Хендлер удаления записи о приеме.
    :param timetable_str: Информация о записи
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    user_id = event.object.message["from_id"]
    cur_user: User = User.get_or_none(User.user_id == user_id)
    current_timetable_str = timetable_str.split("Отменить запись ")[1]
    cur_timetable_obj = get_current_timetable_from_timetable_str(cur_user, current_timetable_str)
    cur_timetable_obj.delete_instance()
    app_logger.info(f"Пользователь {cur_user.full_name} отменил запись {current_timetable_str}")
    vk_api_elem.messages.send(peer_id=user_id,
                              message=f"Запись {current_timetable_str} отменена!",
                              random_id=get_random_id(),
                              keyboard=KEYBOARD)

def get_report_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для формирования отчета о консультациях и отправки администратору
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """

    if str(event.object.message["from_id"]) == str(ADMIN_ID):
        app_logger.info("Запрос отчета о консультациях от администратора")

        # report_text = "Отчет о консультациях на сегодня:\n\nВремя                  Пользователь\n"
        report_text = "Отчет о консультациях на сегодня:\n\n"
        # Получаем все записи Timetable на сегодня.
        today_timetables = Timetable.select().where(Timetable.is_booked == True)
        cur_date = datetime.date.today()
        for timetable in today_timetables:
            if timetable.date != cur_date:
                report_text += f"\nДата: {timetable.date}\n\n"
                cur_date = timetable.date
            cur_user: User = User.get_by_id(timetable.user_id)
            # report_text += (f"{timetable.start_time.strftime("%H:%M")} - {timetable.end_time.strftime("%H:%M")}      "
            #                 f"{cur_user.full_name}, {cur_user.phone}, {cur_user.birthday}, "
            #                 f"{cur_user.address if cur_user.address is not None else ""}\n")
            report_text += (f"Время: {timetable.start_time.strftime("%H:%M")} - {timetable.end_time.strftime("%H:%M")}\n"
                            f"Имя: {cur_user.full_name}\n"
                            f"Телефон: {cur_user.phone}\n"
                            f"Дата рождения: {cur_user.birthday}\n\n")

        report_text += f"\n\nВсего записей: {len(today_timetables)}"

        # Отправляем отчет администратору
        vk_api_elem.messages.send(peer_id=ADMIN_ID,
                                  message=report_text,
                                  random_id=get_random_id(),
                                  keyboard=KEYBOARD)
        return
    app_logger.warning(f"Внимание! Пользователь c id {event.object.message["from_id"]} запросил отчет!")
    vk_api_elem.messages.send(peer_id=event.object.message["from_id"],
                              message="Информация недоступна",
                              random_id=get_random_id())
