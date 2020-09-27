import logging, datetime
from functools import wraps
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters

from .utils import effective_user_name, build_menu

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("STUDENT")
SOLUTION, SIGNATURE = range(2)


def start_solving(update, context):
    # register chat for updates
    context.bot_data['registered_chats'].add(update.effective_chat['id'])
    context.bot_data['solutions'][update.effective_chat['id']] = {}
    context.bot_data['solutions'][update.effective_chat['id']]['photos'] = []
    context.bot_data['solutions'][update.effective_chat['id']]['user'] = update.effective_user
    logger.info(f'Chat {update.effective_chat["id"]} with user {effective_user_name(update)} registered for test')
    query = update.callback_query
    query.answer()
    query.edit_message_text(text='You are registered for test')
    if context.bot_data['active_test']:
        query.message.reply_text('You are starting to solve the test, sign your work first,'
                                 'send me your name and surname like this "Антон Антонов"')
        query.message.reply_photo(photo=context.bot_data['test_img'], caption=context.bot_data['test_caption'])
        return SIGNATURE
    else:
        query.message.reply_text('No active test, I will notify you when it will be created')
        query.message.reply_text('Now you can sign your work, send me your name and surname like this "Антон Антонов"')
        return SIGNATURE


def sign_solutions(update, context):
    signature = update.message.text
    logger.info(f'user {effective_user_name(update)} signed as {signature}')
    context.bot_data['solutions'][update.effective_chat['id']]['signature'] = signature
    update.message.reply_text(f'You have signed as {signature}, now you are ready to start the test')
    return SOLUTION


def send_solution(update, context):
    photos = []
    if context.bot_data['active_test']:
        update.message.reply_text('Gotcha! You can send more solutions')
        context.bot_data['solutions'][update.effective_chat['id']]['photos'].append(update.message.photo[-1])
        # context.bot.send_photo(chat_id=context.bot_data['teacher_chat_id'], photo=update.message.photo[-1],
        #                       caption=f'solution by {effective_user_name(update)}')
        return SOLUTION
    else:
        update.message.reply_text('Unable to send solutions, no active test, press /cancel to end conversation')
        return ConversationHandler.END


def finish(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text='See you next week!')
    logger.info(f'user {effective_user_name(update)} finished test')
    return ConversationHandler.END


def time(update, context):
    rem_time = context.bot_data['time_end'] - datetime.datetime.now()
    logger.info(f'user asked for remaining time {rem_time}')
    update.message.reply_text(f'Remaining time: {rem_time}')

    return SOLUTION
