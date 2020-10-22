import logging, datetime
from functools import wraps
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters

from .utils import permission_check, effective_user_name, test_end_time

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("TEACHER")

TEST, CAPTION, TIMER, START = range(4)


def create_test(update, context):
    logger.info(f'user {effective_user_name(update)} started test creation')
    context.bot_data['teacher_chat_id'] = update.effective_chat['id']
    query = update.callback_query
    query.answer()
    query.edit_message_text(text='You are starting to create test. Upload test image first')
    # update.message.reply_text('You are starting to create test. Upload test image first',
    #                           reply_markup=ReplyKeyboardRemove())
    return TEST


def upload_test(update, context):
    context.bot_data['test_img'] = update.message.photo[-1]
    reply_keyboard = [['Skip']]
    update.message.reply_text('Test uploaded. Now create caption, or skip this step by pressing Skip button',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                               resize_keyboard=True, one_time_keyboard=True))
    return CAPTION


def create_caption(update, context):
    context.bot_data['test_caption'] = None
    if update.message.text != 'Skip':
        context.bot_data['test_caption'] = update.message.text
    update.message.reply_text('Nice, now type test duration in minutes',
                              reply_markup=ReplyKeyboardRemove())
    return TIMER


def set_timer(update, context):
    due = int(update.message.text)
    context.bot_data['test_due'] = due
    buttons = [[InlineKeyboardButton('Start', callback_data=10)]]
    update.message.reply_text(f'Test duration is set to {due} minutes.\n'
                              f'Test creation finished, press the Start button when ready to start',
                              reply_markup=InlineKeyboardMarkup(buttons))
    return START


def start_test(update, context):
    query = update.callback_query
    query.answer()
    # remove old timer job
    if 'timer' in context.bot_data:
        old_job = context.bot_data['timer']
        old_job.schedule_removal()

    if 'notifications' in context.bot_data:
        for notification in context.bot_data['notifications']:
            old_job = notification
            old_job.schedule_removal()
    # set test end time
    test_due = context.bot_data['test_due']
    context.bot_data['test_end'] = datetime.datetime.now() + datetime.timedelta(minutes=test_due)
    logger.info(f'test ends at {test_end_time(context)}')
    # create final alarm
    new_job = context.job_queue.run_once(alarm, test_due * 60, context=context)
    context.bot_data['timer'] = new_job
    # create notifications
    context.bot_data['notifications'] = {}
    duration_list = [3*60, 1*60, 30]
    for duration in duration_list:
        if test_due * 60 - duration > 0:
            job_context = [context, duration]
            new_job = context.job_queue.run_once(notify, test_due * 60 - duration, context=job_context)
            context.bot_data['notifications'][duration] = new_job

    # make test active
    context.bot_data['active_test'] = True
    # send test to all registered chats
    for chat in context.bot_data['registered_chats']:
        context.bot.send_message(chat_id=chat, text=f'New test started, end at {test_end_time(context)}')
        buttons = [[InlineKeyboardButton("Time", callback_data='time_button')]]
        context.bot.send_message(chat_id=chat, text=f'Check how much time left',
                                 reply_markup=InlineKeyboardMarkup(buttons))
        context.bot.send_photo(chat_id=chat, photo=context.bot_data['test_img'],
                               caption=context.bot_data['test_caption'])
    query.edit_message_text(f'Test have started, ends at {test_end_time(context)}')
    return ConversationHandler.END


def alarm(context):
    context.bot_data['active_test'] = False
    for chat in context.bot_data['registered_chats']:
        buttons = [[InlineKeyboardButton('Finish', callback_data='finish_test')]]
        context.bot.send_message(chat_id=chat, text=f"Test ended, now you can't send solutions. "
                                                    f"Press Finish",
                                 reply_markup=InlineKeyboardMarkup(buttons))
    if context.bot_data.get('solutions'):
        context.bot.send_message(chat_id=context.bot_data['teacher_chat_id'],
                                 text=f'Test ended, here are the solutions:')
        solutions = context.bot_data['solutions']
        for chat in solutions:
            solution = solutions[chat]
            if solution.get('photos'):
                context.bot.send_message(chat_id=context.bot_data['teacher_chat_id'],
                                         text=f'user {solution["user"]["first_name"]} {solution["user"]["last_name"]} '
                                              f'signed as {solution["signature"]} sent this:')
                photos = []
                for photo in solution['photos']:
                    photos.append(InputMediaPhoto(media=photo))
                context.bot.send_media_group(chat_id=context.bot_data['teacher_chat_id'],
                                             media=photos, timeout=40)
    else:
        context.bot.send_message(chat_id=context.bot_data['teacher_chat_id'],
                                 text=f'Test ended, no solutions received')
    context.bot_data['registered_chats'] = set()
    context.bot_data['test_end'] = None
    context.bot_data['solutions'] = {}


def notify(job_context):
    context = job_context[0]
    duration = job_context[1]
    for chat in context.bot_data['registered_chats']:
        context.bot.send_message(chat_id=chat, text=f"{duration//60} m {duration%60} s left")
