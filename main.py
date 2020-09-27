import logging, datetime
from functools import wraps
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters, CallbackQueryHandler

from app.config import config
from app import teacher, student
from app.utils import admins, build_menu

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("CHATBOT")


def start(update, context):
    if update.effective_user['id'] in admins:
        buttons = [[InlineKeyboardButton("Create test", callback_data='teacher_button')]]
        update.message.reply_text('Do you want to create new test?',
                                  reply_markup=InlineKeyboardMarkup(buttons))
    else:
        buttons = [[InlineKeyboardButton("Prepare for test", callback_data='student_button')]]
        update.message.reply_text('Do you want to start solving test? '
                                  'If no active test found, you will be registered for the new test',
                                  reply_markup=InlineKeyboardMarkup(buttons))


def cancel(update, context):
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled conversation")
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def main():
    updater = Updater(config.TOKEN, use_context=True)
    # init
    dp = updater.dispatcher
    dp.bot_data['registered_chats'] = set()
    dp.bot_data['active_test'] = False
    dp.bot_data['test_end'] = None
    dp.bot_data['solutions'] = {}
    dp.add_handler(CommandHandler('start', start))
    # teacher side
    test_creation_handler = ConversationHandler(
        entry_points=[CommandHandler('create_test', teacher.create_test),
                      MessageHandler(Filters.regex('^(Create test)$'), teacher.create_test),
                      CallbackQueryHandler(teacher.create_test, pattern='^teacher_button')],
        states={
            teacher.TEST: [MessageHandler(Filters.photo, teacher.upload_test)],
            teacher.CAPTION: [MessageHandler(Filters.text & ~Filters.command, teacher.create_caption)],
            teacher.TIMER: [MessageHandler(Filters.regex('^[1-9]?[0-9]+$'), teacher.set_timer)],
            teacher.START: [MessageHandler(Filters.regex('^(Start)$'), teacher.start_test),
                            CallbackQueryHandler(teacher.start_test)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(test_creation_handler)

    # student side
    test_solution_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^(Start solving)$'), student.start_solving),
                      CallbackQueryHandler(student.start_solving, pattern='^student_button$')],
        states={
            student.SIGNATURE: [MessageHandler(Filters.text & ~Filters.command, student.sign_solutions)],
            student.SOLUTION: [MessageHandler(Filters.photo, student.send_solution),
                               MessageHandler(Filters.regex('^(time)$'), student.time),
                               CommandHandler('time', student.time),
                               MessageHandler(Filters.regex('^(Finish)$'), student.finish),
                               CallbackQueryHandler(student.finish, pattern='^finish_test$')],

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(test_solution_handler)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
