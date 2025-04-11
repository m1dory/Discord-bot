import disnake
from disnake.ext import commands
import asyncio
import random

# токен бота
TOKEN = "Введите свой токен"

# список запрещенных слов
banned_words = []

# Храним количество нарушений для каждого пользователя
violations = {}

# Время мута для разных нарушений (в секундах)
mute_times = {
    1: 10 * 60,  # 10 минут
    2: 60 * 60,  # 1 час
    3: 24 * 60 * 60,  # 1 сутки
    4: None  # Мут на всегда
}

# Создаем экземпляр бота с префиксом "!"
intents = disnake.Intents.default()
intents.message_content = True  # Включаем intent для работы с содержимым сообщений
intents.members = True # Для отслеживания новых участников

bot = commands.Bot(command_prefix="!", intents=intents, test_guilds=[1311764160765362207])


@bot.event
async def on_ready():
    print(f"Bot {bot.user} is ready to work!")


@bot.event
async def on_member_join(member):
    # Находим текстовый канал для приветствий, например, с именем "основной"
    channel = disnake.utils.get(member.guild.text_channels, name="основной")
    if channel:
        # Отправляем приветственное сообщение
        await channel.send(f"👋 Хаюхай, {member.mention}! Как дела?!")
    else:
        print(f"Канал 'основной' не найден на сервере {member.guild.name}.")

    # Автоматически выдаём роль "Новичок", если такая есть
    role = disnake.utils.get(member.guild.roles, name="Новичок")
    if role:
        try:
            await member.add_roles(role)
            await channel.send(f"✨ Роль {role.name} была выдана {member.mention}.")
        except Exception as e:
            print(f"Ошибка при выдаче роли {role.name}: {e}")
    else:
        print(f"Роль 'Новичок' не найдена на сервере {member.guild.name}.")


# Событие для обработки сообщений
@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Игнорируем сообщения от бота

    if message.content.startswith("!"):
        await bot.process_commands(message)  # Даем боту обработать команду
        return

    for word in banned_words:
        if word in message.content.lower():  # Проверяем сообщение на наличие запрещенного слова
            #await message.delete()  # Удаляем сообщение
            await message.channel.send(f"🚫 {message.author.mention}, ваше сообщение было удалено, потому что оно содержит запрещённое слово.", delete_after=1000)

            # Проверяем количество нарушений для пользователя
            user_id = message.author.id
            if user_id not in violations:
                violations[user_id] = 0  # Если нарушений нет, начинаем с 0

            violations[user_id] += 1  # Увеличиваем количество нарушений

            # Получаем количество нарушений
            violation_count = violations[user_id]

            # Применяем мут в зависимости от количества нарушений
            mute_time = mute_times.get(violation_count, mute_times[4])  # Для 4-го нарушения - навсегда

            # Получаем роль для мута
            mute_role = disnake.utils.get(message.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await message.guild.create_role(name="Muted", permissions=disnake.Permissions(send_messages=False))

            # Добавляем роль "Muted" пользователю
            await message.author.add_roles(mute_role)
            await message.channel.send(f"{message.author.mention} был замучен на {mute_time // 60} минут.", delete_after = 1000)

            # Если мут на определенное время, то снимаем его после нужного времени
            if mute_time:
                await asyncio.sleep(mute_time)
                await message.author.remove_roles(mute_role)
                await message.channel.send(f"{message.author.mention} был размучен после {mute_time // 60} минут.")

            return  # Прекращаем выполнение после первого найденного запрещённого слова

    await bot.process_commands(message)  # Позволяет боту продолжать обрабатывать другие команды

@bot.command(name="mute", help="Мутит пользователя на указанное количество минут. Использование: !mute @user time")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: disnake.Member, time: int):
    # Проверка на корректность времени
    if time <= 0:
        await ctx.send("⚠️ Время должно быть больше 0.", delete_after = 5)
        return

    # Проверяем, что роль Muted существует
    mute_role = disnake.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        # Если роль не найдена, создаем ее
        mute_role = await ctx.guild.create_role(name="Muted", permissions=disnake.Permissions(send_messages=False))
        for channel in ctx.guild.text_channels:
            await channel.set_permissions(mute_role, send_messages=False)

    # Проверяем, что роль бота не выше, чем у участника
    if mute_role.position >= ctx.guild.me.top_role.position:
        await ctx.send("❌ Я не могу назначить эту роль, потому что она выше моей роли.", delete_after = 5)
        return

    # Если участник уже имеет роль Muted, мы ничего не делаем
    if mute_role in member.roles:
        await ctx.send(f"⚠️ {member.mention} уже в муте.", delete_after = 5)
        return

    # Добавляем роль Muted участнику
    await member.add_roles(mute_role)
    await ctx.send(f"✅ {member.mention} был замучен на {time} минут.", delete_after = time * 60 + 5)

    # Ожидаем указанное количество времени
    await asyncio.sleep(time * 60)

    # Убираем роль Muted
    await member.remove_roles(mute_role)
    await ctx.send(f"🔓 {member.mention} был размучен после {time} минут.", delete_after = 5)

@bot.command(name="unmute", help="Снимает мут с пользователя. Использование: !unmute @user")
@commands.has_permissions(manage_roles=True)  # Убедитесь, что у бота есть права для управления ролями
async def unmute(ctx, member: disnake.Member):
    # Проверяем, что роль Muted существует
    mute_role = disnake.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        await ctx.send("❌ Роль 'Muted' не найдена на сервере.", delete_after = 5)
        return

    # Проверяем, есть ли у участника роль Muted
    if mute_role not in member.roles:
        await ctx.send(f"⚠️ {member.mention} не замучен.", delete_after = 5)
        return

    # Убираем роль Muted у участника
    await member.remove_roles(mute_role)
    await ctx.send(f"🔓 {member.mention} был размучен.", delete_after = 1000)


@bot.command(name="clear", help="Удалить последние сообщения в текущем канале")
@commands.has_permissions(manage_messages=True)  # Проверка на права
async def clear(ctx, amount: int = 10):
    """
    Удаляет указанное количество сообщений из текущего канала.
    Если количество не указано, по умолчанию удаляется 10 сообщений.
    """
    if amount < 1:
        await ctx.send("⚠️ Укажите положительное количество сообщений для удаления!", delete_after=5)
        return

    # Удаление сообщений
    deleted = await ctx.channel.purge(limit=amount)

    # Подтверждение
    await ctx.send(f"✅ Удалено {len(deleted)} сообщений.", delete_after=1000)


@bot.command(name="add_banned_word", description="Добавить запрещённое слово")
@commands.has_permissions(administrator=True)
async def add_banned_word(ctx, word: str):
    global banned_words

    word = word.lower()

    if word in banned_words:
        await ctx.send(f"Это слово уже есть в списке запрещённых.", delete_after=1000)
    else:
        banned_words.append(word)
        await ctx.send(f"Это слово добавлено в список запрещённых слов.", delete_after=1000)
    #await ctx.message.delete()


@bot.command(name="remove_banned_word")
@commands.has_permissions(administrator=True)
async def remove_banned_word(ctx, word: str):
    global banned_words

    word = word.lower()

    if word not in banned_words:
        await ctx.send(f"Это слово не найдено в списке запрещённых слов.", delete_after=1000)
        return

    banned_words.remove(word)
    await ctx.send(f"Это слово удалено из списка запрещённых слов.", delete_after=1000)
    #await ctx.message.delete()  # Удаляем команду (само сообщение с командой)


@bot.command(name="roll", help="Генерирует случайное число от A до B (включительно) или от 1 до 100, если диапазон не указан.")
async def roll(ctx, a: int = 1, b: int = 100):
    """Генерирует случайное число в указанном диапазоне (по умолчанию от 1 до 100)."""
    if a > b:  # Проверка, что первое число не больше второго
        await ctx.send("⚠️ Первое число должно быть меньше или равно второму.")
        return
    result = random.randint(a, b)
    await ctx.send(f" Результат: {result}")


@bot.command(name="coin", help="Подбрасывает монету. Выдает случайно 'Орел' или 'Решка'.")
async def coin(ctx):
    """Подбрасывает монету."""
    result = random.choice(["Орел", "Решка"])
    await ctx.send(f"🪙 Результат: {result}")


bot.run(TOKEN)
