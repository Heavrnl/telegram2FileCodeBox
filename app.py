import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from telethon import TelegramClient
from telethon.tl.types import InputPeerUser
import asyncio
from FastTelethonhelper import fast_download

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
API_ID = os.environ.get('API_ID')
API_HASH = os.environ.get('API_HASH')

# 创建Telethon客户端
client = TelegramClient('bot_session', API_ID, API_HASH)

# 定义下载文件夹
DOWNLOAD_FOLDER = './downloads/'

# 确保下载文件夹存在
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def progress_bar(current, total):
    return f"下载进度: {current * 100 / total:.1f}%"

async def upload_file(file_path):
    url = 'https://domain/share/file/'
    # 准备文件和表单数据
    with open(file_path, 'rb') as file:
        files = {'file': file}
        data = {
            'expire_value': '1',
            'expire_style': 'day'
        }
        # 发送POST请求
        response = requests.post(url, files=files, data=data)

    # 检查响应
    if response.status_code == 200:
        result = response.json()
        code = result['detail']['code']
        # 构造最终URL
        final_url = f"https://domain/#/?code={code}"
        return final_url
    else:
        logger.error(f"上传失败。状态码: {response.status_code}")
        return None

async def download_file_telethon(message, reply):
    if message.document:
        file_name = message.document.attributes[-1].file_name if message.document.attributes else f"document_{message.document.id}"
    elif message.audio:
        file_name = getattr(message.audio, 'file_name', None) or f"audio_{message.audio.id}.mp3"
    elif message.video:
        file_name = getattr(message.video, 'file_name', None) or f"video_{message.video.id}.mp4"
    elif message.photo:
        file_name = f"photo_{message.photo.id}.jpg"
    else:
        return None

    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
    logger.info(f"正在使用FastTelethonhelper下载文件: {file_name}")
    
    await fast_download(client, message, reply, DOWNLOAD_FOLDER, progress_bar)
    
    return file_path

async def handle_file_or_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"收到来自聊天ID {update.effective_chat.id} 的消息")

    if str(update.effective_chat.id) != CHAT_ID:
        logger.warning(f"忽略来自未授权聊天ID的消息: {update.effective_chat.id}")
        return

    try:
        # 使用Telethon获取消息
        telethon_message = await client.get_messages(InputPeerUser(update.effective_user.id, 0), ids=update.message.message_id)
        
        # 发送下载开始消息
        reply = await update.message.reply_text("开始下载文件...")
        
        # 使用FastTelethonhelper下载文件
        file_path = await download_file_telethon(telethon_message, reply)

        if file_path:
            logger.info("开始上传文件")
            upload_url = await upload_file(file_path)
            if upload_url:
                await update.message.reply_text(f"文件上传成功。访问链接: {upload_url}")
                logger.info(f"文件上传成功: {upload_url}")
            else:
                await update.message.reply_text("文件上传失败。")
                logger.error("文件上传失败")

            # 清理下载的文件
            os.remove(file_path)
            logger.info(f"已删除本地文件: {file_path}")
        else:
            logger.warning("收到的消息不包含文件或媒体")
            await update.message.reply_text("请发送文件、音频、视频或图片。")
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        await update.message.reply_text("处理文件时发生错误，请稍后再试。")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bot正在运行。发送文件、音频、视频或图片给我来上传。')
    logger.info("执行了start命令")

async def run_telethon():
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Telethon client started")

def main() -> None:
    logger.info("Bot启动中...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ATTACHMENT | filters.AUDIO | filters.VIDEO | filters.PHOTO, handle_file_or_media))

    # 启动Telethon客户端
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_telethon())

    logger.info("开始轮询更新...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
