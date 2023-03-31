from http import HTTPStatus
import logging
import os
import sys
import requests
import telegram
import time

from dotenv import load_dotenv

'''ПРИВЕТ МОЙ ЛЮБИМЫЙ РЕВЬЮЕР!'''

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
    """Отправляет запрос к API, узнает статус ДЗ,проверяет ответ API."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise ValueError(f'Проблемы с доступом к API. '
                             f'Код ответа: {response.status_code}')
        response = response.json()
        return response
    except requests.RequestException as e:
        raise ValueError(f'Ошибка при отправке запроса к API: {e}')
    except Exception as e:
        raise ValueError(f'Ошибка при обработке ответа от API: {e}')


def check_response(response):
    """проверка корректности ответа."""
    if not isinstance(response, dict):
        raise TypeError('вернувшееся значение не словарь')

    if ('homeworks' not in response) or ('current_date' not in response):
        raise TypeError(
            'Вернулось пустое значение'
        )
    homework = response.get('homeworks')

    if not isinstance(homework, list):
        raise TypeError('Ключ Homeworks вернулся не списком')

    if not homework:
        raise ValueError(' Домашняя работа не отправленна ')

    if not isinstance(homework[0], dict):
        raise TypeError('Первый вернувшейся элемент homework не словарь')

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
    last_message = ''

    timestamp = int(time.time())
    while True:
        try:
            response_json = get_api_answer(timestamp)
            check_response(response_json)
            response_json['homeworks']
            message = parse_status(response_json['homeworks'][0])
        except Exception as error:
            logging.error(f'Ошибка работы программы{error}')
            message = f'Ошибка работы программы{error}'
        finally:
            if message != last_message:
                send_message(bot, message)
                last_message = message
                timestamp = response_json['current_date']
            else:
                message = 'Данные не обновлялись.'
                logging.info(message)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
