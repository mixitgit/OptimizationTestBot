import logging, datetime
from functools import wraps
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters

from config import config

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("CHATBOT")


admins = list(map(int, config.ADMINS.split()))

TEST, CAPTION, TIMER, START = range(4)
SOLUTION, FINISH = range(2)


def _time_left(current_time, end_time):
    ...

def admin_check(func):
    @wraps(func)
    def wrapped(update, context):
        if update.effective_user['id'] in admins:
            return func(update, context)
        else:
            update.message.reply_text("You don't have permissions for this")
            logger.info(f'user {update.effective_user["id"]} trying to do something')
    return wrapped


@admin_check
def create_test(update, context):
    logger.info(f'user {update.effective_user["id"]} trying to create test')
    context.bot_data['teacher_chat_id'] = update.effective_chat['id']
    update.message.reply_text('You are starting to create test. Upload test image first. To cancel type /cancel')
    return TEST


def upload_test(update, context):
    context.bot_data['test_img'] = update.message.photo[-1]
    reply_keyboard = [['Skip']]
    update.message.reply_text('Test uploaded. Now create caption, or skip this step',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return CAPTION


def create_caption(update, context):
    context.bot_data['test_caption'] = None
    if update.message.text != 'Skip':
        context.bot_data['test_caption'] = update.message.text
    update.message.reply_text('Nice, now set test duration in minutes',
                              reply_markup=ReplyKeyboardRemove())
    return TIMER


# todo add timer
def set_timer(update, context):
    due = int(update.message.text)
    context.bot_data['test_due'] = due
    if due < 0:
        update.message.reply_text('Sorry we can not go back to future!')
        return
    reply_keyboard = [['Start']]
    update.message.reply_text('Test creation finished, press the Start button when ready',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return START


def alarm(context):
    context.bot_data['active_test'] = False
    context.bot_data['test_end'] = None
    for chat in context.bot_data['registered_chats']:
        context.bot.send_message(chat_id=chat, text=f"Test ended, you can't send solutions. See you next week!")
    context.bot.send_message(chat_id=context.bot_data['teacher_chat_id'], text=f'Test ended')
    return ConversationHandler.END


def start_test(update, context):
    # remove old timer job
    if 'timer' in context.bot_data:
        old_job = context.bot_data['timer']
        old_job.schedule_removal()
    # set test end time
    test_due = context.bot_data['test_due']
    context.bot_data['test_end'] = datetime.datetime.now() + datetime.timedelta(minutes=test_due)
    logger.info(f'{datetime.datetime.now()}')
    new_job = context.job_queue.run_once(alarm, test_due*60, context=context)
    context.bot_data['timer'] = new_job

    # make test active
    context.bot_data['active_test'] = True

    # send test to all registered chats
    for chat in context.bot_data['registered_chats']:
        context.bot.send_message(chat_id=chat, text=f'New test started, end at {context.bot_data["test_end"]}')
        context.bot.send_photo(chat_id=chat, photo=context.bot_data['test_img'],
                               caption=context.bot_data['test_caption'])
    update.message.reply_text(f'Test have started, ends at {context.bot_data["test_end"]}')
    return ConversationHandler.END


def cancel(update, context):
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the test creation.")
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def start(update, context):
    # register chat for updates
    context.bot_data['registered_chats'].append(update.effective_chat['id'])
    logger.info(f'Chat {update.message.chat["id"]} '
                f'with user {update.effective_user["first_name"]} {update.effective_user["last_name"]} '
                f'registered for test')

    if context.bot_data['active_test']:
        update.message.reply_text('You are starting to solve the test')
        update.message.reply_photo(photo=context.bot_data['test_img'], caption=context.bot_data['test_caption'])
        return SOLUTION
    else:
        update.message.reply_text('No active test, I will notify you when it will be created')
        return ConversationHandler.END


def send_solution(update, context):
    user = update.message.from_user
    photos = []
    logger.info(f'message: {update.message.photo}')
    reply_keyboard = [['Finish']]
    update.message.reply_text('You can send more solutions or finish test')
    context.bot.send_photo(chat_id=context.bot_data['teacher_chat_id'], photo=update.message.photo[-1],
                           caption=f'solution by {user["first_name"]} {user["last_name"]}')
    return SOLUTION


def finish_test(update, context):
    update.message.reply_text('See you next week.')
    return ConversationHandler.END


def main():
    updater = Updater(config.TOKEN, use_context=True)
    # init
    dp = updater.dispatcher
    dp.bot_data['registered_chats'] = []
    dp.bot_data['active_test'] = False
    dp.bot_data['test_end'] = None
    # teacher side
    test_creation_handler = ConversationHandler(
        entry_points=[CommandHandler('create_test', create_test)],
        states={
            TEST: [MessageHandler(Filters.photo, upload_test)],
            CAPTION: [MessageHandler(Filters.text & ~Filters.command, create_caption)],
            TIMER: [MessageHandler(Filters.regex('^[1-9]?[0-9]+$'), set_timer)],
            START: [MessageHandler(Filters.regex('^(Start)$'), start_test)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(test_creation_handler)

    # student side
    test_solution_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SOLUTION: [MessageHandler(Filters.photo, send_solution),
                       MessageHandler(Filters.regex('^(Finish)$'), finish_test)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(test_solution_handler)
    # dp.add_handler(MessageHandler(Filters.photo, send_solution))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
