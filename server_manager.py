# Импортируем созданный нами класс Server
from server import Server
# Получаем из config.py наш api-token
from config import VK_API_KEY, GROUP_ID, ADMIN_ID


server_1 = Server(VK_API_KEY, GROUP_ID, "server1")
