# minerar redes pro trabalho
import configparser
from pprint import pprint

import networkx as nx
import matplotlib.pyplot as plt
import requests


def connect_to_endpoint(url, headers, params):
    response = requests.request("GET", url, headers=headers, params=params)
    # print(response.status_code)
    # enquanto 429 rate limit exceeded fazer requests enquanto janela n abre novamente
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )

    return response.json()


def user_id(username):
    data_username = username
    get_user_id_url = f'https://api.twitter.com/2/users/by/username/{data_username}'
    user_lookup_info = connect_to_endpoint(get_user_id_url, headers, params={})
    return user_lookup_info['data']['id']


def get_user_network(user_id, next_page_token=None):
    if next_page_token is not None:
        url = f'https://api.twitter.com/2/users/{user_id}/' \
              f'following?pagination_token={next_page_token}&max_results=1000'
    else:
        url = f'https://api.twitter.com/2/users/{user_id}/following?max_results=1000'

    params = {"user.fields": "created_at"}
    json_get_response = connect_to_endpoint(url, headers, params)
    json_get_response['main_node'] = {
        "user_id": user_id,
    }

    try:
        page_token = json_get_response['meta']['next_token']
    except KeyError:
        # esse erro marca qd acontece a ultima página
        page_token = json_get_response['meta']['previous_token']

    return json_get_response, page_token


def users_network_next_page(next_page_token, user_id):
    url = f'https://api.twitter.com/2/users/{user_id}/' \
          f'following?pagination_token={next_page_token}&max_results=1000'

    params = {"user.fields": "created_at"}
    json_get_response = connect_to_endpoint(url, headers, params)
    json_get_response['main_node'] = {
        "user_id": user_id,
    }


def create_hop(ego, main_node, alters):
    for node in alters:
        ego.add_edge(main_node, node['id'])


if __name__ == '__main__':
    config = configparser.RawConfigParser()
    config.read('config.cfg')

    bearer_token = config['tokens']['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    user_id = user_id('yayboechat')

    ego_network = nx.Graph()
    network_page1, page_token = get_user_network(user_id)
    network_page2, page_token = get_user_network(user_id, page_token)
    network = network_page1['data'] + network_page2['data']

    # criação do hop 1
    create_hop(ego_network, user_id, network)
    nx.draw(ego_network)

