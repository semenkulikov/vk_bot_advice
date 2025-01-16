from database.models import User
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger
from config_data.config import BASE_DIR
import os
import datetime


start_text = """
Здравствуйте, {full_name}! Если вы хотите записаться на консультацию, пожалуйста выберите одну из двух зеленых кнопок, расположенных ниже.

Если вас интересует дополнительная информация — выберите кнопку «Частые вопросы», возможно там вы найдете ответ на свой вопрос.

ВАЖНО! Для записи на консультацию, вам должно быть не менее 21 года.
"""


def start_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для обработки сообщений от пользователей.
    :param event: VkBotEvent
    :param vk_api_elem: VkApiMethod
    :return: None
    """
    keyboard = open(os.path.join(BASE_DIR, "keyboards/default.json"), "r", encoding="UTF-8").read()

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
                                  keyboard=keyboard)
    else:
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=start_text.format(full_name=full_name),
                                  random_id=get_random_id(),
                                  keyboard=keyboard)
        if phone is None:
            vk_api_elem.messages.send(peer_id=user_id,
                                      message=f"Внимание! Не удалось получить номер телефона.\n"
                                              f"Напишите его отдельно в формате +79991234567, без номера телефона вы не "
                                              f"сможете записаться на консультацию!",
                                      random_id=get_random_id(),
                                      keyboard=keyboard)
        if birthday is None:
            vk_api_elem.messages.send(peer_id=user_id,
                                      message=f"Внимание! Не удалось получить дату рождения.\n"
                                              f"Напишите ее отдельно в формате 12.13.1415 (день, месяц, год), иначе вы не "
                                              f"сможете записаться на консультацию!",
                                      random_id=get_random_id(),
                                      keyboard=keyboard)
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
                              random_id=get_random_id())


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
                              message=f"Дата рождения успешно добавлена!",
                              random_id=get_random_id())

    user_birthday_list = [int(elem) for elem in user.birthday.split(".")]
    user_birthday = datetime.date(year=user_birthday_list[2], month=user_birthday_list[1],
                                  day=user_birthday_list[0])

    if (datetime.datetime.now().date() - user_birthday).days <= 7665:
        app_logger.warning(f"Внимание! Пользователь {user.full_name} слишком малой! Ему менее 21 года ({birthday})")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message="ВАЖНО! Чтобы я могла записать вас на консультацию, "
                                          "ваш возраст должен быть не менее 21 года.",
                                  random_id=get_random_id())



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
                              message="Спасибо, мы пришлем вам напоминание о времени вашей записи!",
                              random_id=get_random_id())
