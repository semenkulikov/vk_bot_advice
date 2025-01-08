import datetime

from database.models import User, Timetable
from vk_api.bot_longpoll import VkBotEvent
from vk_api.utils import get_random_id
from logger import app_logger


def get_free_time_handler(event: VkBotEvent, vk_api_elem) -> None:
    """
    Хендлер для обработки сообщений от пользователей.
    :param vk_api_elem: VkApiMethod
    :param event: VkBotEvent
    :return: None
    """
    user_id = event.object.message["from_id"]

    # Получение объекта пользователя из БД.
    user = User.get_or_none(User.user_id == user_id)
    app_logger.info(f"Запрос свободного времени от {user.full_name}.")
    if user is None:
        app_logger.warning(f"Внимание! Запрос свободного времени от неизвестного пользователя {user_id}")
    else:
        # Получение свободных часов из БД.
        free_time = get_free_time()

        # Отправляем пользователю список свободного времени.
        vk_api_elem.messages.send(peer_id=user_id,
                                  message=f"Расписание свободных часов на неделю:",
                                  random_id=get_random_id())
        for date, times in free_time.items():
            vk_api_elem.messages.send(peer_id=user_id,
                                      message=f"{date}:\n{'\n'.join(times)}",
                                      random_id=get_random_id())


def get_free_time() -> dict[str, list[str]]:
    """
    Функция для получения свободного времени из БД.
    :return: Словарь, ключ - дата, значение - свободное время в формате HH:MM - HH:MM
    """
    cur_datetime = datetime.datetime.now()
    free_time = {}
    for timetable in Timetable.select().where(Timetable.date >= cur_datetime.date()):
        if not timetable.is_booked:
            free_time.setdefault(timetable.date.strftime("%d.%m.%Y"), []).append(f"{timetable.start_time} - {timetable.end_time}")

    return free_time