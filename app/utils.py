import datetime
from functools import wraps
from .config import config

admins = list(map(int, config.ADMINS.split()))


def permission_check(func):
    @wraps(func)
    def wrapped(update, context):
        if update.effective_user['id'] in admins:
            return func(update, context)
        else:
            update.message.reply_text("You don't have permissions for this")
    return wrapped


def effective_user_name(update):
    return f'{update.effective_user["first_name"]} {update.effective_user["last_name"]}'


def build_menu(buttons,
               n_cols,
               header_buttons=None,
               footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, [header_buttons])
    if footer_buttons:
        menu.append([footer_buttons])
    return menu


def test_end_time(context):
    end_time = context.bot_data.get('test_end')
    if end_time:
        end_time += datetime.timedelta(hours=3)
        return end_time.strftime('%H:%M')

