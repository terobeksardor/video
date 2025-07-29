import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ChatMemberStatus
import re
from functools import lru_cache
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request
import threading
import json
import time
import urllib.parse

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot sozlamalari - Bu qiymatlarni o'zgartiring
BOT_TOKEN = "7626749090:AAFL--dyGniYyUVQ-U0sErxtwOL0qbrytXs"
WEBHOOK_URL = "https://video-fru1.onrender.com/webhook"
PORT = int(os.environ.get("PORT", 8080))
ADMIN_IDS = [6852738257]
DATABASE_PATH = "bot_database.db"

# Tillar
LANGUAGES = {
    'uz': {
        'welcome': """🎬 Video Downloader Bot ga xush kelibsiz!

📱 Quyidagi platformalardan video yuklay olasiz:
• TikTok
• YouTube (Video va Shorts)
• Facebook (Reels va Video)
• Instagram (Reels, Story, Post)

📝 Foydalanish:
Video linkini yuboring va kerakli sifatni tanlang!

👨‍💼 Admin: /admin - Admin panel
📊 Statistika: /stats""",
        'choose_language': '🌐 Tilni tanlang / Choose language / Выберите язык:',
        'language_changed': '✅ Til o\'zgartirildi!',
        'subscription_required': '🔒 Botdan foydalanish uchun quyidagi kanallarga obuna bo\'ling:',
        'subscription_check': '✅ Tekshirish',
        'subscription_success': '✅ Tabriklaymiz! Endi botdan foydalanishingiz mumkin.',
        'subscription_failed': '❌ Siz hali barcha kanallarga obuna bo\'lmadingiz!',
        'send_link': '❌ Iltimos, to\'g\'ri video linkini yuboring!\n\n📱 Qo\'llab-quvvatlanadigan platformalar:\n• TikTok • YouTube • Facebook • Instagram',
        'unknown_platform': '❌ Noma\'lum platforma! Qo\'llab-quvvatlanadigan:\n• TikTok • YouTube • Facebook • Instagram',
        'choose_quality': 'video aniqlandi!\n🎬 Kerakli sifatni tanlang:',
        'downloading': '⏳ Video yuklanmoqda... (3-5 soniya)',
        'file_too_large': '❌ Fayl hajmi juda katta (50MB dan ortiq)',
        'download_error': '❌ Xatolik:',
        'send_error': '❌ Fayl yuborishda xatolik:',
        'admin_only': '❌ Sizda admin huquqi yo\'q!',
        'admin_panel': '👨‍💼 Admin Panel',
        'stats': '📊 Statistika',
        'broadcast': '📢 Xabar yuborish',
        'channels': '⚙️ Kanal sozlamalari',
        'users': '👥 Foydalanuvchilar',
        'no_permission': '❌ Ruxsat yo\'q!',
        'quality_720': '🔥 720p',
        'quality_480': '📱 480p',
        'quality_360': '💾 360p',
        'quality_audio': '🎵 Audio',
        'quality_high': '🔥 Yuqori',
        'quality_medium': '📱 O\'rta',
        'quality_low': '💾 Past'
    },
    'ru': {
        'welcome': """🎬 Добро пожаловать в Video Downloader Bot!

📱 Вы можете скачивать видео с следующих платформ:
• TikTok
• YouTube (Видео и Shorts)
• Facebook (Reels и Видео)
• Instagram (Reels, Story, Post)

📝 Использование:
Отправьте ссылку на видео и выберите нужное качество!

👨‍💼 Админ: /admin - Админ панель
📊 Статистика: /stats""",
        'choose_language': '🌐 Tilni tanlang / Choose language / Выберите язык:',
        'language_changed': '✅ Язык изменен!',
        'subscription_required': '🔒 Для использования бота подпишитесь на следующие каналы:',
        'subscription_check': '✅ Проверить',
        'subscription_success': '✅ Поздравляем! Теперь вы можете пользоваться ботом.',
        'subscription_failed': '❌ Вы еще не подписались на все каналы!',
        'send_link': '❌ Пожалуйста, отправьте правильную ссылку на видео!\n\n📱 Поддерживаемые платформы:\n• TikTok • YouTube • Facebook • Instagram',
        'unknown_platform': '❌ Неизвестная платформа! Поддерживаемые:\n• TikTok • YouTube • Facebook • Instagram',
        'choose_quality': 'видео найдено!\n🎬 Выберите нужное качество:',
        'downloading': '⏳ Загружается видео... (3-5 секунд)',
        'file_too_large': '❌ Размер файла слишком большой (более 50MB)',
        'download_error': '❌ Ошибка:',
        'send_error': '❌ Ошибка отправки файла:',
        'admin_only': '❌ У вас нет прав администратора!',
        'admin_panel': '👨‍💼 Админ Панель',
        'stats': '📊 Статистика',
        'broadcast': '📢 Отправить сообщение',
        'channels': '⚙️ Настройки каналов',
        'users': '👥 Пользователи',
        'no_permission': '❌ Нет разрешения!',
        'quality_720': '🔥 720p',
        'quality_480': '📱 480p',
        'quality_360': '💾 360p',
        'quality_audio': '🎵 Аудио',
        'quality_high': '🔥 Высокое',
        'quality_medium': '📱 Среднее',
        'quality_low': '💾 Низкое'
    },
    'en': {
        'welcome': """🎬 Welcome to Video Downloader Bot!

📱 You can download videos from the following platforms:
• TikTok
• YouTube (Videos and Shorts)
• Facebook (Reels and Videos)  
• Instagram (Reels, Stories, Posts)

📝 Usage:
Send a video link and choose the desired quality!

👨‍💼 Admin: /admin - Admin panel
📊 Statistics: /stats""",
        'choose_language': '🌐 Tilni tanlang / Choose language / Выберите язык:',
        'language_changed': '✅ Language changed!',
        'subscription_required': '🔒 To use the bot, subscribe to the following channels:',
        'subscription_check': '✅ Check',
        'subscription_success': '✅ Congratulations! Now you can use the bot.',
        'subscription_failed': '❌ You haven\'t subscribed to all channels yet!',
        'send_link': '❌ Please send a valid video link!\n\n📱 Supported platforms:\n• TikTok • YouTube • Facebook • Instagram',
        'unknown_platform': '❌ Unknown platform! Supported:\n• TikTok • YouTube • Facebook • Instagram',
        'choose_quality': 'video detected!\n🎬 Choose the desired quality:',
        'downloading': '⏳ Downloading video... (3-5 seconds)',
        'file_too_large': '❌ File size too large (over 50MB)',
        'download_error': '❌ Error:',
        'send_error': '❌ File sending error:',
        'admin_only': '❌ You don\'t have admin rights!',
        'admin_panel': '👨‍💼 Admin Panel',
        'stats': '📊 Statistics',
        'broadcast': '📢 Send message',
        'channels': '⚙️ Channel settings',
        'users': '👥 Users',
        'no_permission': '❌ No permission!',
        'quality_720': '🔥 720p',
        'quality_480': '📱 480p',
        'quality_360': '💾 360p',
        'quality_audio': '🎵 Audio',
        'quality_high': '🔥 High',
        'quality_medium': '📱 Medium',
        'quality_low': '💾 Low'
    }
}

# Thread pool for downloading
executor = ThreadPoolExecutor(max_workers=3)

# Flask app
app = Flask(__name__)

# Global bot reference
bot_application = None

# Ma'lumotlar bazasini yaratish
def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            language TEXT DEFAULT 'uz'
        )
    ''')
    
    # Majburiy kanallar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_name TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Statistika jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date DATE PRIMARY KEY,
            new_users INTEGER DEFAULT 0,
            active_users INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# Cache uchun
@lru_cache(maxsize=100)
def get_required_channels():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT channel_id, channel_name FROM required_channels')
    channels = cursor.fetchall()
    conn.close()
    return channels

# Foydalanuvchi tilini olish
async def get_user_language(user_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_user_language_sync, user_id)

def _get_user_language_sync(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'uz'

# Foydalanuvchi tilini saqlash
async def set_user_language(user_id, language):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _set_user_language_sync, user_id, language)

def _set_user_language_sync(user_id, language):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
    conn.commit()
    conn.close()

# Til tanlash tugmalari
def get_language_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ],
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Matnni olish
async def get_text(user_id, key):
    language = await get_user_language(user_id)
    return LANGUAGES.get(language, LANGUAGES['uz']).get(key, LANGUAGES['uz'][key])

# Foydalanuvchini ma'lumotlar bazasiga qo'shish
async def add_user(user_id, username=None, first_name=None):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _add_user_sync, user_id, username, first_name)

def _add_user_sync(user_id, username, first_name):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, language)
        VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, 'uz'))
    
    today = datetime.now().date()
    if cursor.rowcount > 0:
        # Yangi foydalanuvchi
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (date, new_users, active_users, downloads)
            VALUES (?,
                COALESCE((SELECT new_users FROM daily_stats WHERE date = ?), 0) + 1,
                COALESCE((SELECT active_users FROM daily_stats WHERE date = ?), 0) + 1,
                COALESCE((SELECT downloads FROM daily_stats WHERE date = ?), 0)
            )
        ''', (today, today, today, today))
    else:
        # Mavjud foydalanuvchi
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats (date, new_users, active_users, downloads)
            VALUES (?,
                COALESCE((SELECT new_users FROM daily_stats WHERE date = ?), 0),
                COALESCE((SELECT active_users FROM daily_stats WHERE date = ?), 0) + 1,
                COALESCE((SELECT downloads FROM daily_stats WHERE date = ?), 0)
            )
        ''', (today, today, today, today))
    
    conn.commit()
    conn.close()

# Majburiy kanallarni tekshirish
async def check_user_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    channels = get_required_channels()
    
    if not channels:
        return True
    
    # Parallel ravishda barcha kanallarni tekshirish
    tasks = []
    for channel_id, _ in channels:
        task = _check_single_channel(context, user_id, channel_id)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Agar biron bir kanal False qaytarsa, False qaytaramiz
    for result in results:
        if isinstance(result, bool) and not result:
            return False
    
    return True

async def _check_single_channel(context, user_id, channel_id):
    try:
        member = await context.bot.get_chat_member(channel_id, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return True  # Xato bo'lsa, true qaytaramiz

# Obuna tugmalarini yaratish
async def get_subscription_keyboard(user_id):
    channels = get_required_channels()
    
    if not channels:
        return None
    
    keyboard = []
    for channel_id, channel_name in channels:
        keyboard.append([InlineKeyboardButton(f"📢 {channel_name}", url=f"https://t.me/{channel_id.replace('@', '')}")])
    
    check_text = await get_text(user_id, 'subscription_check')
    keyboard.append([InlineKeyboardButton(check_text, callback_data="check_subscription")])
    
    return InlineKeyboardMarkup(keyboard)

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await add_user(user.id, user.username, user.first_name)
    
    # Foydalanuvchi tilini tekshirish
    user_language = await get_user_language(user.id)
    
    # Agar til tanlanmagan bo'lsa, til tanlash tugmalarini ko'rsatish
    if not user_language or user_language == 'uz':
        # Yangi foydalanuvchi uchun til tanlash
        new_user_check = await _check_new_user(user.id)
        if new_user_check:
            choose_lang_text = LANGUAGES['uz']['choose_language']
            keyboard = get_language_keyboard()
            await update.message.reply_text(choose_lang_text, reply_markup=keyboard)
            return
    
    # Obunani tekshirish
    if not await check_user_subscription(context, user.id):
        keyboard = await get_subscription_keyboard(user.id)
        if keyboard:
            subscription_text = await get_text(user.id, 'subscription_required')
            await update.message.reply_text(subscription_text, reply_markup=keyboard)
            return
    
    welcome_text = await get_text(user.id, 'welcome')
    await update.message.reply_text(welcome_text)

# Yangi foydalanuvchini tekshirish
async def _check_new_user(user_id):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_new_user_sync, user_id)

def _check_new_user_sync(user_id):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT join_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        join_date = datetime.fromisoformat(result[0])
        now = datetime.now()
        # Agar 1 daqiqadan kam vaqt o'tgan bo'lsa, yangi foydalanuvchi
        return (now - join_date).total_seconds() < 60
    return True

# Video linkini aniqlash
@lru_cache(maxsize=50)
def detect_platform(url):
    patterns = {
        'tiktok': r'(?:tiktok.com|vm.tiktok.com)',
        'youtube': r'(?:youtube.com|youtu.be)',
        'facebook': r'(?:facebook.com|fb.watch)',
        'instagram': r'instagram.com'
    }
    
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return None

# Video sifat tugmalarini yaratish
async def get_quality_keyboard(platform, url, user_id):
    # URL ni base64 qilib encode qilamiz uzunlik muammosini oldini olish uchun
    encoded_url = urllib.parse.quote(url, safe='')
    
    keyboard = []
    
    if platform == 'youtube':
        quality_720 = await get_text(user_id, 'quality_720')
        quality_480 = await get_text(user_id, 'quality_480')
        quality_360 = await get_text(user_id, 'quality_360')
        quality_audio = await get_text(user_id, 'quality_audio')
        
        keyboard = [
            [InlineKeyboardButton(quality_720, callback_data=f"dl_720_{encoded_url}")],
            [InlineKeyboardButton(quality_480, callback_data=f"dl_480_{encoded_url}")],
            [InlineKeyboardButton(quality_360, callback_data=f"dl_360_{encoded_url}")],
            [InlineKeyboardButton(quality_audio, callback_data=f"dl_audio_{encoded_url}")]
        ]
    else:
        quality_high = await get_text(user_id, 'quality_high')
        quality_medium = await get_text(user_id, 'quality_medium')
        quality_low = await get_text(user_id, 'quality_low')
        
        keyboard = [
            [InlineKeyboardButton(quality_high, callback_data=f"dl_high_{encoded_url}")],
            [InlineKeyboardButton(quality_medium, callback_data=f"dl_medium_{encoded_url}")],
            [InlineKeyboardButton(quality_low, callback_data=f"dl_low_{encoded_url}")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

# Video yuklab olish
async def download_video(url, quality='best'):
    def _download():
        try:
            temp_dir = tempfile.mkdtemp()
            
            ydl_opts = {
                'outtmpl': f'{temp_dir}/%(title)s.%(ext)s',
                'writesubtitles': False,
                'writeautomaticsub': False,
                'noplaylist': True,
                'extract_flat': False,
                'ignoreerrors': False,
                'no_warnings': True,
                'quiet': True,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_subs': False,
                'writeinfojson': False,
                'writethumbnail': False,
            }
            
            # Sifat sozlamalari
            format_map = {
                '720': 'best[height<=720]/best[width<=1280]/best',
                '480': 'best[height<=480]/best[width<=854]/best',
                '360': 'best[height<=360]/best[width<=640]/best',
                'audio': 'bestaudio[ext=m4a]/bestaudio/best',
                'high': 'best[filesize<50M]/best',
                'medium': 'best[height<=720][filesize<30M]/best[height<=480]',
                'low': 'worst[height>=240]/worst'
            }
            
            ydl_opts['format'] = format_map.get(quality, 'best[filesize<100M]/best')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                return {
                    'success': True,
                    'filename': filename,
                    'title': info.get('title', 'Unknown')[:50] + '...' if len(info.get('title', '')) > 50 else info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'temp_dir': temp_dir
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)[:100] + '...' if len(str(e)) > 100 else str(e)
            }
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, _download)
    return result

# Xabar handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    
    # Obunani tekshirish
    if not await check_user_subscription(context, user.id):
        keyboard = await get_subscription_keyboard(user.id)
        if keyboard:
            subscription_text = await get_text(user.id, 'subscription_required')
            await update.message.reply_text(subscription_text, reply_markup=keyboard)
            return
    
    # URL tekshirish
    if not (message_text.startswith('http://') or message_text.startswith('https://')):
        send_link_text = await get_text(user.id, 'send_link')
        await update.message.reply_text(send_link_text)
        return
    
    platform = detect_platform(message_text)
    
    if not platform:
        unknown_platform_text = await get_text(user.id, 'unknown_platform')
        await update.message.reply_text(unknown_platform_text)
        return
    
    # Sifat tanlash tugmalari
    keyboard = await get_quality_keyboard(platform, message_text, user.id)
    
    platform_names = {
        'tiktok': 'TikTok',
        'youtube': 'YouTube',
        'facebook': 'Facebook',
        'instagram': 'Instagram'
    }
    
    choose_quality_text = await get_text(user.id, 'choose_quality')
    await update.message.reply_text(
        f"📱 {platform_names[platform]} {choose_quality_text}",
        reply_markup=keyboard
    )

# Statistikani yangilash
async def update_download_stats():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _update_download_stats_sync)

def _update_download_stats_sync():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    today = datetime.now().date()
    cursor.execute('''
        INSERT OR REPLACE INTO daily_stats (date, new_users, active_users, downloads)
        VALUES (?,
            COALESCE((SELECT new_users FROM daily_stats WHERE date = ?), 0),
            COALESCE((SELECT active_users FROM daily_stats WHERE date = ?), 0),
            COALESCE((SELECT downloads FROM daily_stats WHERE date = ?), 0) + 1
        )
    ''', (today, today, today, today))
    conn.commit()
    conn.close()

# Callback query handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Til tanlash
    if query.data.startswith("lang_"):
        language = query.data.split("_")[1]
        await set_user_language(query.from_user.id, language)
        
        language_changed_text = await get_text(query.from_user.id, 'language_changed')
        await query.edit_message_text(language_changed_text)
        
        # Welcome xabarini yuborish
        welcome_text = await get_text(query.from_user.id, 'welcome')
        await context.bot.send_message(chat_id=query.message.chat_id, text=welcome_text)
        return
    
    if query.data == "check_subscription":
        if await check_user_subscription(context, query.from_user.id):
            success_text = await get_text(query.from_user.id, 'subscription_success')
            await query.edit_message_text(success_text)
            
            # Welcome xabarini yuborish
            welcome_text = await get_text(query.from_user.id, 'welcome')
            await context.bot.send_message(chat_id=query.message.chat_id, text=welcome_text)
        else:
            failed_text = await get_text(query.from_user.id, 'subscription_failed')
            await query.answer(failed_text, show_alert=True)
        return
    
    if query.data.startswith("dl_"):
        parts = query.data.split("_", 2)
        quality = parts[1]
        encoded_url = parts[2]
        url = urllib.parse.unquote(encoded_url)
        
        # Yuklanish jarayoni haqida xabar
        downloading_text = await get_text(query.from_user.id, 'downloading')
        progress_message = await query.edit_message_text(downloading_text)
        
        try:
            # Video yuklab olish
            result = await download_video(url, quality)
            
            if result['success']:
                # Fayl yuborish
                with open(result['filename'], 'rb') as video_file:
                    caption = f"🎬 {result['title']}\n📤 @{context.bot.username}"
                    
                    # Fayl hajmini tekshirish
                    file_size = os.path.getsize(result['filename'])
                    if file_size > 50 * 1024 * 1024:  # 50MB
                        large_file_text = await get_text(query.from_user.id, 'file_too_large')
                        await progress_message.edit_text(large_file_text)
                    else:
                        await context.bot.send_video(
                            chat_id=query.message.chat_id,
                            video=video_file,
                            caption=caption,
                            supports_streaming=True
                        )
                        await progress_message.delete()
                
                # Vaqtinchalik fayllarni tozalash
                shutil.rmtree(result['temp_dir'], ignore_errors=True)
                
                # Statistikani yangilash
                await update_download_stats()
                
            else:
                error_text = await get_text(query.from_user.id, 'download_error')
                await progress_message.edit_text(f"{error_text} {result['error']}")
                
        except Exception as e:
            send_error_text = await get_text(query.from_user.id, 'send_error')
            await progress_message.edit_text(f"{send_error_text} {str(e)[:100]}")

# == Admin panel ==
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        admin_only_text = await get_text(user_id, 'admin_only')
        await update.message.reply_text(admin_only_text)
        return
    
    stats_text = await get_text(user_id, 'stats')
    broadcast_text = await get_text(user_id, 'broadcast')
    channels_text = await get_text(user_id, 'channels')
    users_text = await get_text(user_id, 'users')
    
    keyboard = [
        [InlineKeyboardButton(stats_text, callback_data="admin_stats")],
        [InlineKeyboardButton(broadcast_text, callback_data="admin_broadcast")],
        [InlineKeyboardButton(channels_text, callback_data="admin_channels")],
        [InlineKeyboardButton(users_text, callback_data="admin_users")]
    ]
    
    admin_panel_text = await get_text(user_id, 'admin_panel')
    await update.message.reply_text(admin_panel_text, reply_markup=InlineKeyboardMarkup(keyboard))

# Statistika ko'rsatish
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(None, _get_stats_sync)
    
    stats_message = f"""📊 Bot Statistikasi:

👥 Jami foydalanuvchilar: {stats['total_users']}
📅 Bugungi yangi foydalanuvchilar: {stats['today_new']}
🔥 Bugungi faol foydalanuvchilar: {stats['today_active']}
⬇️ Bugungi yuklab olishlar: {stats['today_downloads']}

📈 Oxirgi 7 kun:
👥 Yangi foydalanuvchilar: {stats['week_new']}
⬇️ Yuklab olishlar: {stats['week_downloads']}"""

    await update.message.reply_text(stats_message)

def _get_stats_sync():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Jami foydalanuvchilar
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Bugungi statistika
    today = datetime.now().date()
    cursor.execute('SELECT new_users, active_users, downloads FROM daily_stats WHERE date = ?', (today,))
    today_stats = cursor.fetchone()
    
    if today_stats:
        today_new, today_active, today_downloads = today_stats
    else:
        today_new = today_active = today_downloads = 0
    
    # Oxirgi 7 kun statistikasi
    week_ago = today - timedelta(days=7)
    cursor.execute('SELECT SUM(new_users), SUM(downloads) FROM daily_stats WHERE date >= ?', (week_ago,))
    week_stats = cursor.fetchone()
    
    week_new = week_stats[0] if week_stats[0] else 0
    week_downloads = week_stats[1] if week_stats[1] else 0
    
    conn.close()
    
    return {
        'total_users': total_users,
        'today_new': today_new,
        'today_active': today_active,
        'today_downloads': today_downloads,
        'week_new': week_new,
        'week_downloads': week_downloads
    }

# == Webhook orqali Flask server ==
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if request.method == "POST":
            json_data = request.get_json(force=True)
            update = Update.de_json(json_data, bot_application.bot)
            
            # Async update ni process qilish
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot_application.process_update(update))
            loop.close()
            
        return 'ok'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error'

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/health')
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# == Main funksiyasi ==
async def main():
    global bot_application
    
    # Ma'lumotlar bazasini ishga tushirish
    init_database()
    
    # Bot application yaratish
    bot_application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlar qo'shish
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(CommandHandler("admin", admin_panel))
    bot_application.add_handler(CommandHandler("stats", show_stats))
    bot_application.add_handler(CallbackQueryHandler(handle_callback))
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Webhook o'rnatish
    try:
        await bot_application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
    
    # Bot application ni initialize qilish
    await bot_application.initialize()
    await bot_application.start()
    
    logger.info("Bot started successfully!")

def run_flask():
    """Flask serverni alohida threadda ishga tushirish"""
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Flask serverni background threadda ishga tushirish
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Bot ni ishga tushirish
    try:
        asyncio.run(main())
        
        # Server ni ishlatish
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        # Bot ni qayta ishga tushirishga harakat qilish
        time.sleep(5)
        asyncio.run(main())
