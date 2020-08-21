import discord
import pymongo
import asyncio
import random
from pymongo import MongoClient
from random import choice
from discord.ext import commands
from discord.ext.commands import Bot
from discord.voice_client import VoiceClient
from config import settings
from config import audio
from config import text

bot = commands.Bot(command_prefix = settings['prefix'])
bot.remove_command('help')
db_client = MongoClient(settings['db']['host'], settings['db']['port'])
db = db_client[settings['db']['name']]

@bot.command() 
async def mute(ctx):
    #Проверка на наличие прав админа у пользователя
    author = ctx.message.author
    if author.guild_permissions.administrator == False:
        await ctx.send(text['not admin'].format(author.mention))
        return
    #Проверка находится ли пользователь в войсе
    if not hasattr(author.voice,'channel'):
        await ctx.send(text['not voice'].format(author.mention))
        return
    voice = author.voice.channel 
    #Проверяем есть ли подключение к войсу или создаем его
    voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    if voice_client is None or not voice_client.is_connected():
        voice_client = await voice.connect()
    #Воспроизводим аудио, если оно не играет
    if not voice_client.is_playing():
        voice_client.play(discord.FFmpegPCMAudio(random.choice(audio['mute'])))
    #Получаем список пользователей имеющих специальные разрешения в канале
    whitelist = [bot.user]
    for userrole in voice.overwrites.keys():
        if type(userrole) == discord.Member:
            whitelist.append(userrole)
    #Мут всех пользователей за исключением предыдущих
    for member in voice.members:
         #Если нашли пользователя в списке или он админ, то скипаем
        skip = False
        for user in whitelist:
            if member == user or member.guild_permissions.administrator == True:
                skip = True
                break
        if skip:
            continue
        #Иначе мутаем
        user = db.muted_users.find_one({"user_id" : member.id})
        if user is None:
            user = {}
            user["user_id"] = member.id
            user["guild"] = member.guild.id
            db.muted_users.insert_one(user)
        await member.edit(mute = True)
    await ctx.send(text['mute'].format(voice.name))

@bot.command() 
async def unmute(ctx):
    #Проверка на наличие прав админа у пользователя
    author = ctx.message.author
    if author.guild_permissions.administrator == False:
        await ctx.send(text['not admin'])
        return
    #Получаем список замутанных пользователей и размутываем
    guild = ctx.message.guild
    for muted_user in db.muted_users.find():
        if muted_user['guild'] == guild.id:
            user = discord.utils.find(lambda m: m.id == muted_user['user_id'], guild.members)
            db.muted_users.delete_one(muted_user)
            await user.edit (mute = False)
    #Проверяем есть ли подключение к войсу или создаем его
    voice_client = discord.utils.get(ctx.bot.voice_clients, guild=ctx.guild)
    if voice_client is not None and voice_client.is_connected():
        #Воспроизводим аудио, если оно не играет
        if not voice_client.is_playing():
            voice_client.play(discord.FFmpegPCMAudio(random.choice(audio['unmute'])))
            await asyncio.sleep(settings['delay'])
            await voice_client.disconnect()
    await ctx.send(text['unmute'])

@bot.command()
async def help(ctx):
    await ctx.send(text['help'])


@bot.event
async def on_ready():
    #Выставляем статус
    activity = discord.Game(name=text['game status'], type=3)
    await bot.change_presence(status=discord.Status.idle, activity=activity)

bot.run(settings['token'])