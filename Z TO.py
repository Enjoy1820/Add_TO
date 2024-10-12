from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from tortoise import Tortoise, fields
from tortoise.models import Model
from datetime import datetime, timedelta



dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


# Инициализация базы данных
async def init_db():
    await Tortoise.init(
        db_url='sqlite://db.sqlite3',
        modules={'models': ['__main__']}
    )
    await Tortoise.generate_schemas()


# Модель для хранения записей о ТО
class ServiceRecord(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    created_date = fields.DatetimeField(auto_now=True)
    service_type = fields.CharField(max_length=2)
    service_date = fields.DatetimeField()
    price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)
    title = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "service_records"


# Список типов ТО
TYPE_CHOICES = {
    'OL': 'OIL',  # Масло
    'FL': 'Filter',  # Фильтр
    'SP': 'Support',  # Тормозные колодки
    'FS': 'Full Service',  # Полное ТО
}


# Команда для добавления записи о ТО
@dp.message_handler(commands=['add_service'])
async def add_service_record(message: types.Message):
    args = message.get_args().split()
    if len(args) < 2:
        await message.reply('Используйте: /add_service <тип_ТО> <дата в формате дд-мм-гггг>')
        return

    service_type = args[0].upper()
    if service_type not in TYPE_CHOICES:
        await message.reply('Неверный тип ТО. Доступные типы: ' + ', '.join(TYPE_CHOICES.keys()))
        return

    try:
        service_date = datetime.strptime(args[1], '%d-%m-%Y')
    except ValueError:
        await message.reply('Неверный формат даты. Используйте формат дд-мм-гггг')
        return

    user_id = message.from_user.id

    # Удаляем старую запись того же типа await ServiceRecord.filter(user_id=user_id, service_type=service_type).delete()

    # Добавляем новую запись
    await ServiceRecord.create(user_id=user_id, service_type=service_type, service_date=service_date)

    await message.reply(f'Запись о ТО "{TYPE_CHOICES[service_type]}" добавлена на {service_date.strftime("%d-%m-%Y")}')


# Команда для отображения профиля пользователя
@dp.message_handler(commands=['profile'])
async def show_profile(message: types.Message):
    user_id = message.from_user.id
    records = await ServiceRecord.filter(user_id=user_id).all()

    if not records:
        await message.reply('Нет записей о ТО.')
        return

    profile_text = 'Ваши записи о ТО:\n'
    for record in records:
        next_service_date = record.service_date + timedelta(days=180)
        profile_text += f'- {TYPE_CHOICES[record.service_type]}: {record.service_date.strftime("%d-%m-%Y")} (следующая замена: {next_service_date.strftime("%d-%m-%Y")})\n'

    # Кнопка для вывода всех последних ТО keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("Показать все ТО", callback_data='show_all_services'))
    await message.reply(profile_text, reply_markup=keyboard)


# Обработка нажатия кнопки "Показать все ТО"
@dp.callback_query_handler(lambda c: c.data == 'show_all_services')
async def button_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    records = await ServiceRecord.filter(user_id=user_id).all()

    if not records:
        await bot.answer_callback_query(callback_query.id, text='Нет записей о ТО.')
        return

    all_services_text = 'Все последние записи о ТО:\n'

