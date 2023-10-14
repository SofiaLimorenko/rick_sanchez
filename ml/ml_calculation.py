import pandas as pd
import numpy as np

import folium
import requests
from tqdm import tqdm
from geopy.distance import geodesic
import random
import datetime


def plot_place_of_user(location):
    # Определяем координаты центра и масштаб
    center = [20, 0]
    zoom = 2

    # Создаем карту и задаем центр и масштаб
    m = folium.Map(location=center, zoom_start=zoom)

    # Наносим аэропорты на карту
    folium.Marker(location=[location[0], location[1]],
                  radius=5,
                  popup='Your posittion',
                  fill=True,
                  icon=folium.Icon(color='green'),
                  fill_opacity=0.9).add_to(m)
    # Для красоты добавляем отображение координат (при нажатии в любом месте карты)
    m.add_child(folium.LatLngPopup())

    # Отображаем карту
    return m


def get_pedestrian_route(api_key, start_location, end_location):
    base_url = "http://www.mapquestapi.com/directions/v2/route"
    params = {
        'key': api_key,
        'from': f"{start_location[0]},{start_location[1]}",
        'to': f"{end_location[0]},{end_location[1]}",
        'routeType': 'pedestrian',
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if data['info']['statuscode'] == 0:
        # Извлекаем координаты маршрута из сегмента линии
        route = data['route']['legs'][0]['maneuvers']
        route_points = [(step['startPoint']['lat'], step['startPoint']['lng']) for step in route]
        # Добавляем конечную точку маршрута
        route_points.append((end_location[0], end_location[1]))
        return route_points
    else:
        raise Exception(f"Error: {data['info']['messages'][0]}")


def plot_pedestrian_route(api_key, start_location, end_location):
    # Определяем координаты центра и масштаб
    center = [(start_location[0] + end_location[0]) / 2, (start_location[1] + end_location[1]) / 2]
    zoom = 15

    # Создаем карту и задаем центр и масштаб
    m = folium.Map(location=center, zoom_start=zoom, tiles="Stamen Terrain")

    # Наносим начальную и конечную точки на карту
    folium.Marker(location=start_location,
                  popup='Start',
                  icon=folium.Icon(color='green')).add_to(m)

    folium.Marker(location=end_location,
                  popup='End',
                  icon=folium.Icon(color='red')).add_to(m)

    # Получаем координаты маршрута для пешехода
    route_points = get_pedestrian_route(api_key, start_location, end_location)

    # Строим линию маршрута
    folium.PolyLine(locations=route_points, color='blue').add_to(m)

    # Для красоты добавляем отображение координат (при нажатии в любом месте карты)
    m.add_child(folium.LatLngPopup())

    # Отображаем карту
    return m, route_points


def generate_balance(df, df_offices):
    ATM_balance = [np.random.choice(range(0, 300000)) for i in range(len(df))]
    officies_balance = [np.random.choice(range(0, 1000000)) for i in range(len(df_offices))]

    df['ATM_balance'] = ATM_balance
    df_offices['officies_balance'] = officies_balance

    return df, df_offices


def needed_amount(amount_of_money, df, df_offices):
    df, df_offices = generate_balance(df, df_offices)

    df = df[df['ATM_balance'] >= amount_of_money]
    df_offices = df_offices[df_offices['officies_balance'] >= amount_of_money]

    return df, df_offices


def generate_office_work_time(amount_of_money, df, df_offices):
    df, df_offices = needed_amount(amount_of_money, df, df_offices)
    office_work_time = ['09:00-20:00',
                        '07:00-19:00',
                        '08:00-18:00',
                        '10:00-20:00',
                        '09:00-21:00',
                        'выходной']

    office_work_time_per_individual = [np.random.choice(office_work_time) for i in range(len(df_offices))]
    office_work_time_per_legal = [np.random.choice(office_work_time) for i in range(len(df_offices))]
    df_offices['office_work_time_per_individual'] = office_work_time_per_individual
    df_offices['office_work_time_per_legal'] = office_work_time_per_legal
    df_offices.reset_index(drop=True, inplace=True)

    return df, df_offices


def generate_operations_in_officies(amount_of_money, df, df_offices):
    df, df_offices = generate_office_work_time(amount_of_money, df, df_offices)

    operations_in_officies = {'Открыть вклад': 15 / 60,
                              'Открыть дебетовую карту': 10 / 60,
                              'Закрыть вклад': 14 / 60,
                              'Взять кредит': 30 / 60,
                              'Купить валюту': 5 / 60,
                              'Продать валюту': 6 / 60,
                              'Перевести деньги внутри страны': 7 / 60,
                              'Перевести деньги за рубеж': 18 / 60,
                              'Открыть ипотеку': 25 / 60,
                              'Разменять деньги': 2 / 60}

    num_operations = random.randint(3, 10)  # случайное количество операций от 3 до 10
    operations = [random.sample(list(operations_in_officies.keys()), num_operations) for i in range(len(df_offices))]
    df_offices['operations'] = operations

    return df, df_offices, operations_in_officies


def time_for_action_user(amount_of_money, action, df, df_offices):
    df, df_offices, operations_in_officies = generate_operations_in_officies(amount_of_money, df, df_offices)
    df_offices = df_offices[df_offices['operations'].apply(lambda x: action in x)].copy()
    df_offices['time_for_action'] = operations_in_officies[action]
    return df, df_offices, operations_in_officies


def natural_or_legal_user(user_type):
    if user_type == 'Физ.лицо':
        return 'Физ лицо'
    else:
        return 'Юр лицо'


def is_working_office_time(user_time, time_for_action_fraction, time_range):
    try:
        start, end = map(lambda x: pd.to_datetime(x).time(), time_range.split('-'))

        user_time = pd.to_datetime(user_time).time()

        # Вычисление времени с учетом time_for_action
        offset_minutes = int(time_for_action_fraction * 60)
        time_to_check = datetime.datetime.combine(datetime.date.today(), user_time) + datetime.timedelta(
            minutes=offset_minutes)

        return start <= time_to_check.time() <= end
    except:
        return False  # выходной


def work_or_no(amount_of_money, time_of_enter_user, df, df_offices, user_type, action):
    df, df_offices, operations_in_officies = time_for_action_user(amount_of_money, action, df, df_offices)
    type_of_user = natural_or_legal_user(user_type)

    if type_of_user == 'Физ лицо':
        df_offices['work_or_no'] = df_offices.office_work_time_per_individual.apply(
            lambda x: is_working_office_time(user_time=time_of_enter_user,
                                             time_for_action_fraction=
                                             df_offices['time_for_action'].reset_index(drop=True)[0],
                                             time_range=x))

    else:
        df_offices['work_or_no'] = df_offices.office_work_time_per_legal.apply(
            lambda x: is_working_office_time(user_time=time_of_enter_user,
                                             time_for_action_fraction=
                                             df_offices['time_for_action'].reset_index(drop=True)[0],
                                             time_range=x))

    return df, df_offices


def load_levels(amount_of_money, time_of_enter_user, df, df_offices, user_type, action):
    df, df_offices = work_or_no(amount_of_money, time_of_enter_user, df, df_offices, user_type, action)
    levels = [random.randint(1, 10) for _ in range(len(df_offices))]
    df_offices['Workload level'] = levels
    return df, df_offices


def calculate_route_length(route_points):
    total_distance = 0
    try:
        for i in range(len(route_points) - 1):
            distance = geodesic(route_points[i], route_points[i + 1]).meters
            total_distance += distance
        return total_distance
    except:
        return np.NaN


def plot_pedestrian_route(api_key, start_location, end_location):
    route_points = get_pedestrian_route(api_key, start_location, end_location)

    length = calculate_route_length(route_points)
    return length


def calc_promej_distance(api_key, amount_of_money, time_of_enter_user, df, df_offices, user_type, action,
                         start_location):
    df, df_offices = load_levels(amount_of_money, time_of_enter_user, df, df_offices, user_type, action)
    distances_length = []
    for i in tqdm(range(len(df_offices))):
        end_location = (df_offices.loc[i]['latitude'], df_offices.loc[i]['longitude'])
        distances_length.append(plot_pedestrian_route(api_key, start_location, end_location))

    df_offices['distance'] = distances_length
    return df, df_offices


def calc_final_distance(api_key, amount_of_money, time_of_enter_user, df, df_offices, user_type, action,
                        start_location):
    df, df_offices = calc_promej_distance(api_key, amount_of_money, time_of_enter_user, df, df_offices, user_type,
                                          action, start_location)
    df_offices['find_distance'] = df_offices['distance'] + ((df_offices['Workload level'] * 6 / 60) * 4) * 1000
    return df, df_offices


def need_wheelchair(user_need_wheelchair):
    if user_need_wheelchair == True:
        return True
    else:
        return False


def is_blind(user_blind):
    if user_blind == True:
        return True
    else:
        return False


def final_check_and_result(api_key, amount_of_money, time_of_enter_user, df, df_offices, user_type, action,
                           start_location, user_need_wheelchair, user_blind):
    df, df_offices = calc_promej_distance(api_key, amount_of_money, time_of_enter_user, df, df_offices, user_type,
                                          action, start_location)

    if len(df_offices) == 0:
        if need_wheelchair(user_need_wheelchair):
            df = df[df['services.wheelchair.serviceActivity'] == 'AVAILABLE'].copy()
        if is_blind(user_blind):
            df = df[df['services.blind.serviceActivity'] == 'AVAILABLE'].copy()

        distances_length = []
        for i in tqdm(range(len(df))):
            end_location = (df.loc[i]['latitude'], df.loc[i]['longitude'])
            distances_length.append(
                plot_pedestrian_route('lzxMVB3UWB0BzEBwDAq45JwDl3TOFKjY', start_location, end_location))

        df['distance'] = distances_length

        return df.sort_values(by='distance')[0]

    else:
        return df_offices.sort_values(by='find_distance')[0]
