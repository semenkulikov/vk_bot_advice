import datetime
import peewee
from config_data.config import BASE_DIR
import os

db = peewee.SqliteDatabase(os.path.join(BASE_DIR, "database/database.db"))


class BaseModel(peewee.Model):
    """ Базовая модель """
    class Meta:
        database = db


class User(BaseModel):
    """ Модель пользователя """
    user_id = peewee.CharField(unique=True)
    full_name = peewee.CharField(null=False)
    phone = peewee.CharField(null=True)
    address = peewee.CharField(null=True)
    birthday = peewee.DateField(null=True)

class Timetable(BaseModel):
    """ Модель для расписания графика свободных часов """
    user_id = peewee.ForeignKeyField(User, backref="timetables", null=True)
    date = peewee.DateField(null=False)
    start_time = peewee.TimeField(null=False)
    end_time = peewee.TimeField(null=False)
    is_booked = peewee.BooleanField(default=False)



def create_models():
    db.create_tables(BaseModel.__subclasses__())


def create_time_tables():
    """ Функция для генерирования графика расписания консультаций на неделю. """
    cur_datetime = datetime.datetime.now()
    for i in range(6):
        cur_date = cur_datetime + datetime.timedelta(days=i)
        if cur_date.weekday() not in [5, 6]:  # Будни, кроме выходных
            for start_time in ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]:
                end_time = start_time.split(":")[0] + ":59"
                Timetable.create(date=cur_date, start_time=start_time, end_time=end_time)

def delete_time_tables():
    """ Функция для удаления старых устаревших записей графика (вчерашних и ранее) """
    cur_datetime = datetime.datetime.now()
    Timetable.delete().where(Timetable.date < cur_datetime.date()).execute()
