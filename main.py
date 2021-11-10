import json
import requests
import time
from pprint import pprint
from datetime import datetime
from datetime import date
from tqdm import tqdm

with open('tokens.json', encoding='utf-8') as file:
    # Получаем токен из json-файла формата: {
    #   "tokens": {
    #     "VK": "XXX",
    #   }
    # }
    # Так как требовалось, чтобы токен облачного хранилища был во входных данных,
    # он получен далее в программе - в функции ya_script.
    data = json.load(file)
    token_vk = data['tokens']['VK']


class UserVK:
    # Класс для пользователя вк, содержит в виде переменных имя, фамилию, id и "никнейм" - конец ссылки на страницу.
    def __init__(self, url: str):
        # init через users.get получает численное id для вк, так как его наличие в ссылке не гарантировано.
        self.nickname = url.split('/')[-1]
        url_get_id = 'https://api.vk.com/method/users.get'
        params = {
            'user_ids': self.nickname,
            'access_token': token_vk,
            'v': '5.131'
        }
        res = requests.get(url_get_id, params=params).json()
        self.id = res['response'][0]['id']
        self.name = res['response'][0]['first_name']
        self.surname = res['response'][0]['last_name']

    def get_profile_photos(self):
        # Этот метод получает данные всех фото профиля, добавляет название и размер файла для каждого фото
        # в список, который является значением словаря с ключом Profile и добавляет эту пару ключ-значение
        # в словарь log_data. В список photo_data добавляется словарь {'Profile': {x: y}}, где х - это название файла,
        # а y - ссылка на него.
        global photo_data
        global log_data
        url_get_photos = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': self.id,
            'album_id': 'profile',
            'extended': 1,
            'photo_sizes': 1,
            'rev': 1,
            'access_token': token_vk,
            'v': '5.131'
        }
        res = requests.get(url_get_photos, params=params).json()
        duplicate_check = []
        pic_data = {}
        album_data = {'Profile': []}
        if amount > res['response']['count']:
            count = res['response']['count']
        else:
            count = amount
        for i in tqdm(range(count)):
            pic = res['response']['items'][i]
            likes = pic['likes']['count']
            pic_url = pic['sizes'][-1]['url']
            size = pic['sizes'][-1]['type']
            if likes in duplicate_check:
                ts = int(pic['date'])
                creation_date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
                pic_data[f'{likes}_{creation_date}.jpg'] = pic_url
                album_data['Profile'].append({"file_name": f'{likes}_{creation_date}.jpg', "size": f"{size}"})
            else:
                duplicate_check.append(likes)
                pic_data[f'{likes}.jpg'] = pic_url
                album_data['Profile'].append({"file_name": f'{likes}.jpg', "size": f"{size}"})
        log_data['photos'].append(album_data)
        photo_data.append({'Profile': pic_data})

    def get_wall_photos(self):
        # Метод аналогичен методу get_profile_photos, но работает с фото со стены.
        global photo_data
        global log_data
        url_get_photos = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': self.id,
            'album_id': 'wall',
            'extended': 1,
            'photo_sizes': 1,
            'rev': 1,
            'access_token': token_vk,
            'v': '5.131'
        }
        res = requests.get(url_get_photos, params=params).json()
        pic_data = {}
        duplicate_check = []
        album_data = {'Wall': []}
        if amount > res['response']['count']:
            count = res['response']['count']
        else:
            count = amount
        for i in tqdm(range(count)):
            pic = res['response']['items'][i]
            likes = pic['likes']['count']
            pic_url = pic['sizes'][-1]['url']
            size = pic['sizes'][-1]['type']
            if likes in duplicate_check:
                ts = int(pic['date'])
                creation_date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
                pic_data[f'{likes}_{creation_date}.jpg'] = pic_url
                album_data['Wall'].append({"file_name": f'{likes}_{creation_date}.jpg', "size": f"{size}"})
            else:
                duplicate_check.append(likes)
                pic_data[f'{likes}.jpg'] = pic_url
                album_data['Wall'].append({"file_name": f'{likes}.jpg', "size": f"{size}"})
        log_data['photos'].append(album_data)
        photo_data.append({'Wall': pic_data})


def vk_script():
    # Скрипт, который результатом своей работы создает файл log_{никнейм}.json, который хранит названия и размеры всех
    # файлов для бэкапа на облако, а также готовит список словарей photo_data с названиями и ссылками на файлы
    # для загрузки в облако.
    global backup_data
    global log_data
    user = input('Введите адрес страницы вк: ')
    vk = UserVK(user)
    backup_data = vk.name + '_' + vk.surname + '_' + f'{date.today()}'
    pprint('Получаем фото из вк:')
    if album_code == 0:
        vk.get_profile_photos()
    elif album_code == 1:
        vk.get_wall_photos()
    elif album_code == 2:
        vk.get_profile_photos()
        vk.get_wall_photos()
    else:
        print('Ошибка: неверный код альбома!')
    with open(f'log_{vk.nickname}.json', 'w') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


class YaUploader:
    # Класс содержащий в себе переменную токен для яндекс.диска и все необходимые методы для сохранения фото в облако.
    def __init__(self, token):
        self.token = token

    def create_folder(self):
        # Метод, создающий папку "имя_фамилия_сегодняшняя_дата" для хранения всех фото определенного пользователя.
        create_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token)
        }
        params = {"path": f'{backup_data}'}
        requests.put(create_url, headers=headers, params=params).json()

    def create_sub_folder(self, pic_type):
        # Метод, создающий подпапки для фото из каждого альбома.
        create_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token)
        }
        params = {"path": f'{backup_data}/{pic_type}'}
        requests.put(create_url, headers=headers, params=params).json()

    def upload(self, location,  pic_type):
        # Метод, который загружает фото в созданные раннее папки.
        files = photo_data[location][pic_type]
        for i in tqdm(files.keys()):
            upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'OAuth {}'.format(self.token)
            }
            params = {"path": f'{backup_data}/{pic_type}/{i}', "url": f'{files.get(i)}'}
            requests.post(upload_url, headers=headers, params=params).json()


def ya_script():
    # Скрипт, который загружает на яндекс.диск все файлы из photo_data, полученного в результате vk_script
    token_ya = input('Введите токен своего яндекс.диска: ')
    ya = YaUploader(token_ya)
    ya.create_folder()
    ref = 0
    pprint('Загружаем фото на яндекс.диск:')
    for i in photo_data:
        ya.create_sub_folder(next(iter(i)))
        ya.upload(ref, next(iter(i)))
        ref += 1


if __name__ == '__main__':
    photo_data = []
    log_data = {'photos': []}
    backup_data = ''

    amount = int(input('Введите количество последних фото для бекапа: '))
    pprint('Укажите код альбома, который вы хотите сохранить.')
    album_code = int(input('(0 - профиль, 1 - стена, 2 - все вышеперечисленное): '))
    vk_script()
    time.sleep(0.5)
    ya_script()
