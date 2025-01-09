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



