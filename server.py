import vk_api.vk_api
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.bot_longpoll import VkBotEventType
from vk_api.utils import get_random_id
from logger import app_logger
from handlers.user_handlers import start_handler, often_questions_handler
from handlers.timetable_handlers import get_free_time_handler
from handlers.reservation_handlers import reservation_date_handler, reservation_time_handler, reservation_handler

import re


class Server:

    def __init__(self, api_token, group_id, server_name: str = "Empty"):
        # Даем серверу имя
        self.server_name = server_name

        # Для Long Poll
        self.vk = vk_api.VkApi(token=api_token)

        # Для использования Long Poll API
        self.long_poll = VkBotLongPoll(self.vk, group_id)

        # Для вызова методов vk_api
        self.vk_api = self.vk.get_api()

    def send_msg(self, send_id, message):
        """
        Отправка сообщения через метод messages.send
        :param send_id: vk id пользователя, который получит сообщение
        :param message: содержимое отправляемого письма
        :return: None
        """
        self.vk_api.messages.send(peer_id=send_id,
                                  message=message,
                                  random_id=get_random_id())

    def send_test_message(self, admin_id):
        self.send_msg(admin_id, "Сервер запущен!")
        app_logger.info("Тестовое сообщение отправлено!")

    def start(self):

        app_logger.info("Сервер запущен! Начинаю слушать сообщения...")
        for event in self.long_poll.listen():  # Слушаем сервер
            try:
                # Пришло новое сообщение
                if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
                    if event.object.message["text"] == "Узнать свободное время":
                        get_free_time_handler(event, self.vk_api)
                    elif event.object.message["text"] == "Частые вопросы":
                        often_questions_handler(event, self.vk_api)
                    elif event.object.message["text"] == "Личный прием":
                        reservation_date_handler(event, self.vk_api, online_advice=False)
                    elif event.object.message["text"] == "Онлайн прием":
                        reservation_date_handler(event, self.vk_api, online_advice=True)
                    # Обработка текстовых сообщений - дат вида 2025-10-01 через регулярное выражение
                    elif re.match(r"\d{4}-\d{2}-\d{2}", event.object.message["text"]):
                        reservation_time_handler(event, self.vk_api, event.object.message["text"])

                    # Обработка текстовых сообщений - времени бронирования вида (day) HH:MM - HH:MM
                    # через регулярное выражение.
                    elif re.match(r"\(\w+\) \d{2}:\d{2}:\d{2} - \d{2}:\d{2}:\d{2}",
                                  event.object.message["text"]):
                        reservation_handler(event, self.vk_api, event.object.message["text"])
                    else:
                        # Пользователь запустил бота
                        start_handler(event, self.vk_api)
            except Exception as ex:
                app_logger.error(f"Ошибка в работе сервера: {str(ex)}")

