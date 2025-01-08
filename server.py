import vk_api.vk_api
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.bot_longpoll import VkBotEventType
from vk_api.utils import get_random_id
from logger import app_logger


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
            # Пришло новое сообщение
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.from_chat:
                    app_logger.info("New message from chat")
                elif event.from_user:
                    app_logger.info("New message from user")
                app_logger.info("ФИО: " + self.get_user_name(event.object.message["from_id"]))
                app_logger.info("From: " + self.get_user_city(event.object.message["from_id"]))
                app_logger.info("Text: " + event.object.message["text"])
                app_logger.info(" --- ")

    def get_user_name(self, user_id):
        """ Получаем имя пользователя"""
        try:
            user_obj = self.vk_api.users.get(user_id=user_id)[0]
            return f"{user_obj['first_name']} {user_obj['last_name']}"
        except Exception as e:
            app_logger.error(f"Error getting user name: {e}")
            return None

    def get_user_city(self, user_id):
        """ Получаем город пользователя"""
        try:
            return self.vk_api.users.get(user_id=user_id, fields="city")[0]["city"]['title']
        except Exception as e:
            app_logger.error(f"Error getting user city: {e}")
            return None

