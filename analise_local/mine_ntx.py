# minerar redes pro trabalho
import configparser
from pprint import pprint

import networkx as nx
from networkx.readwrite import json_graph
import matplotlib.pyplot as plt
import requests
import json
import copy
from time import sleep


def connect_to_endpoint(url, headers, params):
    response = requests.request("GET", url, headers=headers, params=params)

    if response.status_code == 429:
        print('429 aqui... tentando outro token')
        bearer_token_v1 = config['tokens']['APP_BEARER_TOKEN_V1']
        new_headers = {"Authorization": "Bearer {}".format(bearer_token_v1)}
        response = requests.request("GET", url, headers=new_headers, params=params)
        while response.status_code == 429:
            print('vamo esperar pra ver oq da')
            sleep(180)
            response = requests.request("GET", url, headers=new_headers, params=params)
            print('esperei 3min pra tentar e consegui', response.status_code)
        print('a resposta foi', response.status_code)

    if response.status_code != 200 and response.status_code != 429:
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


def get_user_network_v1(user_id, next_page_token=None):
    url = f'https://api.twitter.com/1.1/friends/ids.json?user_id={user_id}&count=20'
    friends_ids = connect_to_endpoint(url, headers, params={})

    return friends_ids['ids']


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
        try:
            page_token = json_get_response['meta']['previous_token']
        except KeyError:
            page_token = None
            print('Apenas 1 página de seguidores')

    return json_get_response, page_token


def create_hop(ego, main_node, alters):
    for ego_node in alters:
        ego.add_edge(main_node, ego_node)


def write_network_json(ego_network, username):
    json_file = open(f"redes/nt_{username}.json", "w+")
    data = json_graph.node_link_data(ego_network)
    json_string = json.dumps(data)
    json_file.write(json_string)
    json_file.close()

    nx.draw(ego_network)
    plt.savefig(f'rede_exemplos/nt_{username}.png')


if __name__ == '__main__':
    config = configparser.RawConfigParser()
    config.read('config.cfg')

    bearer_token = config['tokens']['APP_BEARER_TOKEN']
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    user_id = user_id('yayboechat')

    ego_network = nx.Graph()
    network = get_user_network_v1(user_id)

    # criação do hop 1
    create_hop(ego_network, user_id, network)
    print('primeiro hop ok')

    current_nodes = copy.deepcopy(ego_network.nodes())
    for node in current_nodes:
        if not node == user_id:
            print('pegando prox hop')
            node_network = get_user_network_v1(node)
            create_hop(ego_network, node, node_network)

    write_network_json(ego_network, 'yayboechat')



    # print(ego_network.adj)

