import logging, datetime
from functools import wraps
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters, CallbackQueryHandler

from app.config import config
from app import teacher, student
from app.utils import admins, build_menu, effective_user_name

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("CHATBOT")


def start(update, context):
    if config.DEV:
        buttons = [[InlineKeyboardButton("Create test", callback_data='teacher_button')]]
        update.message.reply_text('Do you want to create new test?',
                                  reply_markup=InlineKeyboardMarkup(buttons))
        buttons = [[InlineKeyboardButton("Prepare for test", callback_data='student_button')]]
        update.message.reply_text('Do you want to start solving test? '
                                  'If no active test found, you will be registered for the new test',
                                  reply_markup=InlineKeyboardMarkup(buttons))
    else:
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
    logger.info(f"User {effective_user_name(update)} canceled conversation")
    if update.effective_chat['id'] in context.bot_data['registered_chats']:
        context.bot_data['registered_chat'].remove(update.effective_chat['id'])
        logger.info(f"Chat with user {effective_user_name(update)} removed from registered chats")
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def time(update, context):
    query = update.callback_query
    query.answer()
    if context.bot_data['test_end']:
        rem_time = context.bot_data['test_end'] - datetime.datetime.now()
        logger.info(f'user asked for remaining time {rem_time}')
        button = InlineKeyboardButton("Time", callback_data='time_button')
        keyboard = InlineKeyboardMarkup.from_button(button)
        query.edit_message_text(text=f'Remaining time: {str(rem_time).split(".")[0]}', reply_markup=keyboard)
    else:
        query.edit_message_text(text=f'No active test')


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
        entry_points=[CallbackQueryHandler(teacher.create_test, pattern='^teacher_button')],
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
                               MessageHandler(Filters.regex('^(Finish)$'), student.finish),
                               CallbackQueryHandler(student.finish, pattern='^finish_test$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(test_solution_handler)
    dp.add_handler(CallbackQueryHandler(time, pattern='^time_button$'))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
