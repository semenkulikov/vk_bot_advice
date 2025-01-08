import peewee

db = peewee.SqliteDatabase("database/database.db")


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


def create_models():
    db.create_tables(BaseModel.__subclasses__())
