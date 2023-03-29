import logging
import os
import sys
import requests
import telegram
import time

from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    format='%(asctime)s, %(name)s, %(levelname)s, %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    encoding='utf-8')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

root_logger = logging.getLogger()
root_logger.addHandler(console_handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщения от бота в телеграм."""
    try:
        chat_id = TELEGRAM_CHAT_ID
        bot.send_message(chat_id, message)
        logging.debug('Сообщение отправленно')
    except Exception as e:
        logging.error(f'Ошибка при отправке сообщения: {e}')
        raise TypeError(f'Неудачная отправка сообщения: {e}')


def get_api_answer(timestamp):
    """Отправляет запрос к API, чтобы узнать статус домашней работы."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == 200:
            response = response.json()
            return response
        else:
            raise ValueError(f'Проблемы с доступом к API.'
                             f'Код ответа: {response.status_code}')
    except Exception as e:
        raise ValueError(f'Запрос к Api неудачен {e}')


def check_response(response):
    """Response check."""
    if not isinstance(response, dict):
        raise TypeError('Error with API response type')

    if ('homeworks' not in response) or ('current_date' not in response):
        raise TypeError(
            'Emty reply from API'
        )
    homework = response.get('homeworks')

    if not isinstance(homework, list):
        raise TypeError('Homeworks type is not list')

    return homework


def parse_status(homework):
    """В случае изменения статуса ДЗ присылает уведомление об этом."""
    timestamp = int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    response = response.json()
    if 'error' in response:
        raise KeyError(
            f"Произошла ошибка при запросе API: {response['error']}")

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('В дз нет ключа')

    if not homework_status:
        raise ValueError('В статусе ДЗ отсутствует значение')

    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except Exception as e:
        raise KeyError(f'статус неизвестен{e}')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'

def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Нет одной из переменных!')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    timestamp = int(time.time())
    while True:
        try:
            response_json = get_api_answer(timestamp)
            check_response(response_json)
            print(response_json['homeworks'])
            if response_json['homeworks']:
                print(response_json['homeworks'][0])
                message = parse_status(response_json['homeworks'][0])
                send_message(bot, message)
                timestamp = response_json['current_date']
            else:
                message = 'Данные не обновлялись.'
                logging.info(message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logging.error(f'Ошибка работы программы{error}')
            error_message = f'Ошибка работы программы{error}'
            send_message(bot, error_message)
            time.sleep(RETRY_PERIOD)

if __name__ == '__main__':
    main()
