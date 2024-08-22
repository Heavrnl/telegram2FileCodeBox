import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# 配置日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')


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


async def handle_file_or_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info(f"收到来自聊天ID {update.effective_chat.id} 的消息")

    if str(update.effective_chat.id) != CHAT_ID:
        logger.warning(f"忽略来自未授权聊天ID的消息: {update.effective_chat.id}")
        return

    file_obj = None
    if update.message.document:
        file_obj = update.message.document
        file_name = file_obj.file_name
    elif update.message.audio:
        file_obj = update.message.audio
        file_name = file_obj.file_name or f"audio_{file_obj.file_id}.mp3"
    elif update.message.video:
        file_obj = update.message.video
        file_name = file_obj.file_name or f"video_{file_obj.file_id}.mp4"
    elif update.message.photo:
        file_obj = update.message.photo[-1]  # Get the largest photo size
        file_name = f"photo_{file_obj.file_id}.jpg"

    if file_obj:
        logger.info(f"收到文件: {file_name}")
        file = await file_obj.get_file()
        logger.info(f"正在下载文件: {file_name}")
        await file.download_to_drive(file_name)

        logger.info("开始上传文件")
        upload_url = await upload_file(file_name)
        if upload_url:
            await update.message.reply_text(f"文件上传成功。访问链接: {upload_url}")
            logger.info(f"文件上传成功: {upload_url}")
        else:
            await update.message.reply_text("文件上传失败。")
            logger.error("文件上传失败")

        # 清理下载的文件
        os.remove(file_name)
        logger.info(f"已删除本地文件: {file_name}")
    else:
        logger.warning("收到的消息不包含文件或媒体")
        await update.message.reply_text("请发送文件、音频、视频或图片。")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bot正在运行。发送文件、音频、视频或图片给我来上传。')
    logger.info("执行了start命令")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bot正在运行。发送文件给我来上传。')
    logger.info("执行了start命令")


def main() -> None:
    logger.info("Bot启动中...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ATTACHMENT | filters.AUDIO | filters.VIDEO | filters.PHOTO, handle_file_or_media))

    logger.info("开始轮询更新...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()