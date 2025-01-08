# Импортируем созданный нами класс Server
from server import Server
# Получаем из config.py наш api-token
from config import VK_API_KEY, GROUP_ID, ADMIN_ID


server1 = Server(VK_API_KEY, GROUP_ID, "server1")

server1.send_test_message(ADMIN_ID)
