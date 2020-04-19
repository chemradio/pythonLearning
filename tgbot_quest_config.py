bot_token = ''
admin_id = 247066990
attachments = '/Users/timurtimaev/Desktop/'
max_file_size = 1048576
postgresql_credentials = {
    'database': 'postgres',
    'user': 'postgres',
    'password': '',
    'host': '127.0.0.1',
    'port': "5432"
}

# __________________________________________________________________________

start_text = 'Hi baby! Starting your interview right now!'
blame_text = 'Wrong answer.\nPlease read the question carefully!\n\n'
max_size_exceed_text = 'Max file size exceeded\n\n'
stupid_text = ['', blame_text, max_size_exceed_text]

# __________________________________________________________________________
tables = ({
        'question_base_name': 'tgbot_questions',
        'question_id': 'question_id',
        'question_text': 'question_text',
        'question_type': 'question_type',
        'answer_types': 'answer_types',
        'attachment': 'attachment'
     }, {
        'answer_base_name': 'tgbot_answers',
        'answer_id': 'answer_id',
        'question_id': 'question_id',
        'tg_user_id': 'tg_user_id',
        'tg_user_nick': 'tg_user_nick',
        'question_type': 'question_type',
        'answer': 'answer',
        'answer_date': 'answer_date'
    })
filepath = attachments
