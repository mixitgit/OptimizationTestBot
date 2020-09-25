import logging
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
    context.bot_data['test_caption'] = update.message.text
    update.message.reply_text('Nice, now set the timer',
                              reply_markup=ReplyKeyboardRemove())
    return TIMER


def set_timer(update, context):
    reply_keyboard = [['Start']]

    update.message.reply_text('Test creation finished, press the Start button when ready',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    logger.info(f'user {update.effective_user["id"]} trying to create test')
    return START


def start_test(update, context):
    ...
    return ConversationHandler.END


def cancel(update, context):
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the test creation.")
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def start(update, context):
    update.message.reply_text('You are starting to solve the test')
    update.message.reply_photo(photo=context.bot_data['test_img'], caption=context.bot_data['test_caption'])
    return SOLUTION


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
    dp = updater.dispatcher

    # teacher side
    test_creation_handler = ConversationHandler(
        entry_points=[CommandHandler('create_test', create_test)],
        states={
            TEST: [MessageHandler(Filters.photo, upload_test)],
            CAPTION: [MessageHandler(Filters.text & ~Filters.command, create_caption)],
            TIMER: [MessageHandler(Filters.text & ~Filters.command, set_timer)],
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
