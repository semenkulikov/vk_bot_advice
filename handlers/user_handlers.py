from database.models import User
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger
from config_data.config import BASE_DIR
import os


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
                                  message=f"Привет, {full_name}! Выбери любую из кнопок ниже для начала работы.",
                                  random_id=get_random_id(),
                                  keyboard=keyboard)
    else:
        user = User.create(user_id=user_id,
                          full_name=full_name,
                          phone=phone,
                          address=address,
                          birthday=birthday)
        app_logger.info(f"Новый пользователь {full_name} добавлен в базу.")
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Привет, {full_name}! Я - бот для бронирования консультаций. Выбери любую из кнопок ниже для начала работы.",
                                  random_id=get_random_id(),
                                  keyboard=keyboard)

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
