import discord
import feedparser
import asyncio
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from keep_alive import keep_alive
from apscheduler.schedulers.asyncio import AsyncIOScheduler
keep_alive()
load_dotenv()  # .env에서 환경변수 불러오기 (로컬 실행 시 필요)

TOKEN = os.getenv('TOKEN')
CHANNEL_DATA_FILE = 'channels.json'

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

scheduler = AsyncIOScheduler()
latest_post_link = None

def load_channels():
    try:
        with open(CHANNEL_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_channels(channels):
    with open(CHANNEL_DATA_FILE, 'w') as f:
        json.dump(channels, f)

auto_channels = load_channels()

async def fetch_and_post_patchnote():
    global latest_post_link

    feed = feedparser.parse("https://discord.com/blog/rss.xml")
    if not feed.entries:
        return

    latest_entry = feed.entries[0]

    if latest_post_link != latest_entry.link:
        latest_post_link = latest_entry.link
        for channel_id in auto_channels:
            channel = client.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title=latest_entry.title,
                    url=latest_entry.link,
                    description=latest_entry.summary,
                    color=discord.Color.blurple()
                )
                embed.set_footer(text="디스코드 공식 블로그 패치노트")
                await channel.send(embed=embed)

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    await tree.sync()
    print('✅ Slash commands synced')
    scheduler.add_job(fetch_and_post_patchnote, 'interval', hours=1)
    scheduler.start()

@client.event
async def on_guild_join(guild):
    await tree.sync(guild=guild)
    print(f'✅ Synced slash commands to new guild: {guild.name}')

# 슬래시 커맨드
@tree.command(name="패치노트자동", description="패치노트 자동 전송을 이 채널에 설정하거나 해제합니다.")
async def patchnote_auto(interaction: discord.Interaction, 설정: str):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("🚫 이 명령어는 서버 관리자만 사용할 수 있어요.", ephemeral=True)
        return

    await handle_patchnote_command(interaction.channel.id, 설정, interaction=interaction)

# 레거시 커맨드
@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith('!패치노트자동'):
        if not message.author.guild_permissions.manage_guild:
            await message.channel.send("🚫 이 명령어는 서버 관리자만 사용할 수 있어요.")
            return

        command = message.content.strip().split()
        if len(command) < 2:
            await message.channel.send("사용법: `!패치노트자동 on` 또는 `!패치노트자동 off`")
            return

        설정 = command[1]
        await handle_patchnote_command(message.channel.id, 설정, message=message)

# 실제 처리 함수
async def handle_patchnote_command(channel_id, 설정, interaction=None, message=None):
    if 설정.lower() == 'on':
        if channel_id not in auto_channels:
            auto_channels.append(channel_id)
            save_channels(auto_channels)
            text = "✅ 이 채널에 자동으로 패치노트를 전송합니다."
        else:
            text = "⚠️ 이 채널은 이미 자동 전송이 설정되어 있어요."
    elif 설정.lower() == 'off':
        if channel_id in auto_channels:
            auto_channels.remove(channel_id)
            save_channels(auto_channels)
            text = "❌ 이 채널의 자동 전송이 중지되었습니다."
        else:
            text = "⚠️ 이 채널은 자동 전송이 설정되어 있지 않아요."
    else:
        text = "사용법: `on` 또는 `off`를 입력하세요."

    if interaction:
        await interaction.response.send_message(text)
    elif message:
        await message.channel.send(text)

client.run(TOKEN)
