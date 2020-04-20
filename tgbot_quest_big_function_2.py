import logging
import psycopg2
import os.path
import requests
import csv
from datetime import datetime
from tgbot_quest_config import tables
from tgbot_quest_config import bot_token
from tgbot_quest_config import postgresql_credentials
from tgbot_quest_config import max_file_size
from tgbot_quest_config import filepath
from tgbot_quest_config import start_text
from tgbot_quest_config import stupid_text
from tgbot_quest_config import admin_id
from pprint import pprint
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler)


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgreDBHandler:
    conn = psycopg2.connect(
        database=postgresql_credentials['database'],
        user=postgresql_credentials['user'],
        password=postgresql_credentials['password'],
        host=postgresql_credentials['host'],
        port=postgresql_credentials['port']
    )
    cur = conn.cursor()

    def create_tables(self):
        # this creates default tables in POSTGRESQL
        self.cur.execute(f'''CREATE TABLE {tables[0]['question_base_name']}
             ({tables[0]['question_id']} SERIAL PRIMARY KEY,
             {tables[0]['question_text']} TEXT,
             {tables[0]['question_type']} INT,
             {tables[0]['answer_types']} TEXT [],
             {tables[0]['attachment']} TEXT);''')

        self.cur.execute(f'''CREATE TABLE {tables[1]['answer_base_name']}
             ({tables[1]['answer_id']} SERIAL PRIMARY KEY,
             {tables[1]['question_id']} TEXT,
             {tables[1]['tg_user_id']} INT,
             {tables[1]['tg_user_nick']} TEXT,
             {tables[1]['question_type']} INT,
             {tables[1]['answer']} TEXT,
             {tables[1]['answer_date']} timestamp without time zone);''')

        self.conn.commit()

    def drop_tables(self):
        # this DROPS or DELETES question and answer tables in a DB
        self.cur.execute(f'''DROP TABLE {tables[0]['question_base_name']}, {tables[1]['answer_base_name']}''')
        self.conn.commit()

    def create_template_questions(self):
        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
    {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
    {tables[0]['attachment']}) VALUES ('How are you?', 1, NULL, 'photo1.jpg')"""
        )

        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
        {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
        {tables[0]['attachment']}) VALUES ('Do you agree?', 2, ARRAY['Yes', 'No'], NULL)"""
        )

        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
        {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
        {tables[0]['attachment']}) VALUES ('Send me a doc or audio!', 3, ARRAY['document', 'audio'], NULL)"""
        )

        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
        {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
        {tables[0]['attachment']}) VALUES ('Send me a pic or video!', 3, ARRAY['photo', 'video'], NULL)"""
        )

        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
        {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
        {tables[0]['attachment']}) VALUES ('Send me a any attached file!', 3, ARRAY['any'], NULL)"""
        )

        self.conn.commit()

    def add_question_db(self, question_text='Question Text', question_type=1, answer_types='NULL', attachment='NULL'):
        # this adds a new question to a QUESTIONS table in a DB
        # provide any attribute you want.
        # mandatory attribute - question_text
        self.cur.execute(
            f"""INSERT INTO {tables[0]['question_base_name']} (
        {tables[0]['question_text']}, {tables[0]['question_type']}, {tables[0]['answer_types']},
        {tables[0]['attachment']}) VALUES ('{question_text}', {question_type}, {answer_types}, {attachment})"""
        )

        self.conn.commit()

    def fetch_question_db(self, question_id):
        # fetches the question from QUESTIONS table based on question_id
        self.cur.execute(f"""SELECT question_id, question_text, question_type, answer_types, attachment
    FROM {tables[0]['question_base_name']} WHERE question_id = %s""", (question_id,))
        row = self.cur.fetchone()
        return row

    def get_columns_questions_db(self):
        # fetches COLUMN NAMES in a QUESTIONS table in a DB
        # used for creating question dict
        self.cur.execute(
            f"""SELECT column_name FROM information_schema.columns WHERE table_name = '{tables[0]['question_base_name']}'""")
        col_names = self.cur.fetchall()
        return col_names

    def generate_question_dict(self, question):
        # creates a DICT with key,value 'question table column name':'data' for a specific question
        question_dict = {}
        col = self.get_columns_questions_db()
        quest = self.fetch_question_db(question)
        for i in range(len(col)):
            question_dict[f'{col[i][0]}'] = quest[i]
        return question_dict

    def write_answer_db(self, answer):
        # writes user answer into ANSWERS table in a DB
        dt = datetime.now()
        self.cur.execute(
            f"""INSERT INTO {tables[1]['answer_base_name']} 
            ({tables[1]['question_id']}, {tables[1]['tg_user_id']}, {tables[1]['tg_user_nick']}, 
            {tables[1]['question_type']}, {tables[1]['answer']}, {tables[1]['answer_date']}) 
            VALUES ({answer['question_id']}, {answer['tg_user_id']}, '{answer['tg_user_nick']}', 
            {answer['question_type']}, '{answer['answer']}', %s)""", (dt,))

        self.conn.commit()

    def get_latest_answer(self, user_id):
        # returns latest user answered question_id
        # if none, returns 0
        self.cur.execute(f"""SELECT question_id, answer_date FROM {tables[1]['answer_base_name']}
        WHERE answer_date = (SELECT MAX(answer_date) FROM {tables[1]['answer_base_name']} WHERE tg_user_id = '{user_id}')""")
        rows = self.cur.fetchone()
        if rows:
            return int(rows[0])
        else:
            return 0

    def check_user_answers(self, user_id):
        # check if user already participated in survey
        self.cur.execute(
            f"""SELECT EXISTS(SELECT question_id FROM {tables[1]['answer_base_name']} WHERE tg_user_id = '{user_id}')""")
        rows = self.cur.fetchone()
        return bool(rows[0])

    def get_number_questions(self):
        # get total number of questions in db
        self.cur.execute(f"""SELECT COUNT(*) FROM {tables[0]['question_base_name']};""")
        row = self.cur.fetchone()
        return row[0]

    def delete_user_answers(self, user_id):
        # erase all previous user answers from a DB
        if self.check_user_answers(user_id):
            print('Already participated. Deleting previous answers.')
            self.cur.execute(f"""DELETE FROM {tables[1]['answer_base_name']} WHERE tg_user_id = '{user_id}'""")
            self.conn.commit()
        else:
            print(f'User {user_id} is a newcomer. No previous answers stored')

    def admin_get_column_names(self):
        # get all questions' 'question_texts'
        question_texts = []
        self.cur.execute(f"""SELECT question_text FROM tgbot_questions""")
        list_of_tuples = self.cur.fetchall()
        for tuple in list_of_tuples:
            question_texts.append(tuple[0])
        return question_texts

    def get_all_respondents_id(self):
        users_list = []
        self.cur.execute(f"""SELECT tg_user_id FROM tgbot_answers""")
        users_repeat = self.cur.fetchall()
        for user in users_repeat:
            users_list.append(user[0])
        users = set(users_list)
        return users

    def admin_get_answers(self, user_id, period):
        answers = []
        question_count = self.get_number_questions()
        self.cur.execute(f"""SELECT answer_date, tg_user_id, answer
                            FROM tgbot_answers
                            WHERE tg_user_id = {user_id} AND age(answer_date) < '{period} days'""")
        rows = self.cur.fetchall()
        if rows:
            date = rows[0][0].strftime("%Y/%m/%d, %H:%M")
            user_dict = [date, user_id]
            for row in rows:
                user_dict.append(row[2])
            if len(rows) < question_count:
                for i in range(question_count - len(rows)):
                    user_dict.append(None)
            return user_dict
        else:
            return

    def get_file_questions(self):
        file_questions = []
        self.cur.execute(f"""SELECT question_id FROM tgbot_questions WHERE question_type =3""")
        rows = self.cur.fetchall()
        for row in rows:
            file_questions.append(row[0])
        return file_questions


class AdminHandler:
    pg = PostgreDBHandler()

    def get_all_answers_list(self, period):
        total_answers = []
        for user in self.pg.get_all_respondents_id():
            if self.pg.admin_get_answers(user, period):
                total_answers.append(self.pg.admin_get_answers(user, period))
            else:
                continue
        return total_answers

    def generate_dl_link(self, file_id):
        tg_api = 'https://api.telegram.org/'
        request_url1 = tg_api + 'bot' + bot_token + '/getFile?file_id=' + file_id
        r = requests.get(request_url1)
        json_response = r.json()
        file_path = json_response['result']['file_path']
        request_url2 = tg_api + 'file/bot' + bot_token + '/' + file_path
        return request_url2

    def create_csv(self, period):
        header = self.pg.admin_get_column_names()
        header.insert(0, 'User_ID')
        header.insert(0, 'Date')
        total_answers = self.get_all_answers_list(period)
        # print(total_answers)
        file_questions_ids = self.pg.get_file_questions()

        for i in range(len(total_answers)):
            for question in file_questions_ids:
                position = (question + 2 -1)
                if total_answers[i][position]:
                    file_id = total_answers[i][position]
                    dl_link = self.generate_dl_link(file_id)
                    total_answers[i][position] = dl_link
        with open('output.csv', 'w') as output:
            csv_out = csv.writer(output)
            csv_out.writerow(header)
            for row in total_answers:
                csv_out.writerow(row)

    def send_csv(self, update, context):
        update.message.reply_document(document=open('output.csv', 'rb'))
        update.message.reply_text('Click /start again to generate new report', reply_markup=ReplyKeyboardRemove())


pg = PostgreDBHandler()
# pg.drop_tables()
# pg.create_tables()
# pg.create_template_questions()
admin = AdminHandler()
intervals = [['1 day', '7 days', '30 days']]


def start(update, context):
    message_dict = update.message.to_dict()
    if message_dict['from']['id'] == admin_id:
        start_admin(update, context)
        return
    else:
        update.message.reply_text(start_text, reply_markup=ReplyKeyboardRemove())

        user_id = message_dict['from']['id']
        pg.delete_user_answers(user_id)
        ask_question(update, context, flag=0, question_id=1)


def start_admin(update, context):
    update.message.reply_text('Please click the time interval for the results:',
                              reply_markup=ReplyKeyboardMarkup(intervals))


def ask_question(update, context, flag, question_id):
    message_dict = update.message.to_dict()
    # user_id = message_dict['from']['id']
    # current_question = pg.get_latest_answer(username)
    # current_question += 1
    current_question = question_id
    current_question_dict = pg.generate_question_dict(current_question)
    question_text = current_question_dict['question_text']
    question_type = current_question_dict['question_type']
    reply_kb_markup = [[]]

    if question_type == 2:
        for option in current_question_dict['answer_types']:
            reply_kb_markup[0].append(option)

    if current_question_dict['attachment']:
        # in case there's a file
        if os.path.isfile(f'{filepath}{current_question_dict["attachment"]}'):
            update.message.reply_document(document=open(f"{filepath}{current_question_dict['attachment']}", 'rb'))
    if current_question_dict['question_type'] == 2:
        # in case there are answer options
        update.message.reply_text(f'{stupid_text[flag]}{question_text}',
                                  reply_markup=ReplyKeyboardMarkup(reply_kb_markup, one_time_keyboard=True))
    else:
        # general purpose asking
        update.message.reply_text(f'{stupid_text[flag]}{question_text}',
                                  reply_markup=ReplyKeyboardRemove())
    return


def admin_reply_analyzer(update, context):
    message_dict = update.message.to_dict()
    if 'text' in message_dict:
        if message_dict['text'] in intervals[0]:
            admin.create_csv(message_dict['text'])
            admin.send_csv(update, context)
            return
        else:
            update.message.reply_text('Sorry, Please just click the button.')
    else:
        update.message.reply_text("Sorry, I can't understand you.")
    return


def reply_analyzer(update, context):
    message_dict = update.message.to_dict()
    pprint(message_dict)
    if message_dict['from']['id'] == admin_id:
        admin_reply_analyzer(update, context)
    else:
        flag = 0

        if pg.get_latest_answer(message_dict['from']['id']):
            db_last_answer = pg.get_latest_answer(message_dict['from']['id'])
        else:
            db_last_answer = 0
        if db_last_answer >= pg.get_number_questions():
            end_of_questions(update, context)
            return
        current_question = db_last_answer + 1
        dt = datetime.now()
        current_question_dict = pg.generate_question_dict(current_question)
        question_type = current_question_dict['question_type']
        answer_types = current_question_dict['answer_types']

        user_data = {'question_id': current_question,
                     'tg_user_id': message_dict['from']['id'],
                     'question_type': current_question_dict['question_type'],
                     'answer_date': dt}

        if 'username' in message_dict['from']:
            user_data['tg_user_nick'] = message_dict['from']['username']
        else:
            user_data['tg_user_nick'] = 'Not specified'

        if question_type == 1:
            if 'text' in message_dict:
                user_data['answer'] = update.message.text[:5000]
            else:
                flag = 1

        elif question_type == 2:
            if 'text' in message_dict:
                if message_dict['text'] in answer_types:
                    user_data['answer'] = update.message.text
                else:
                    flag = 1
            else:
                flag = 1

        elif question_type == 3:
            full_array = ['audio', 'video', 'photo', 'document']
            required_array = []
            print(bool(message_dict['photo']))
            if answer_types == ['any']:
                required_array = full_array
            else:
                for item in answer_types:
                    required_array.append(item)
            print(required_array)

            for item in required_array:
                print(item)
                if item == 'photo' and message_dict['photo']:
                    print('photo pass')
                    if message_dict['photo'][0]['file_size'] < max_file_size:
                        print('photo size pass')
                        user_data['answer'] = message_dict['photo'][0]['file_id']
                        break
                    else:
                        flag = 2
                elif item in message_dict and item != 'photo':
                    print('general pass')
                    if message_dict[item]['file_size'] < max_file_size:
                        print('general size pass')
                        # print(message_dict[item])
                        user_data['answer'] = message_dict[item]['file_id']
                        break
                    else:
                        flag = 2

            if 'answer' in user_data:
                print(user_data['answer'])
            elif flag == 2:
                user_data['answer'] = 'max size exceed'
            else:
                user_data['answer'] = 'wrong'
                flag = 1

        else:
            print('error question')


        if flag == 0:
            pg.write_answer_db(user_data)
            current_question += 1

        if current_question > pg.get_number_questions():
            end_of_questions(update, context)
            return

        ask_question(update, context, flag, current_question)
        return


def end_of_questions(update, context):
    update.message.reply_text('We have no more questions for you right now.'
                              '\n\nIf you want to pass the test once more just hit: /start')
    return


# def cancel(update, context):
#     global proper_start
#     proper_start = False
#     message_dict = update.message.to_dict()
#     user_id = message_dict['from']['id']
#     pg.delete_user_answers(user_id)
#     update.message.reply_text('Bye! I hope we can talk again some day.',
#                               reply_markup=ReplyKeyboardRemove())
#     return


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def helper(update, context):
    update.message.reply_text('Start the interview: /start'
                              '\nCancel the interview at any time: /cancel'
                              '\nHelp is /help'
                              '\nGood Luck!')


def main():
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    # dp.add_handler(CommandHandler('cancel', cancel))
    dp.add_handler(CommandHandler('help', helper))
    dp.add_handler(MessageHandler(Filters.all, reply_analyzer))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
