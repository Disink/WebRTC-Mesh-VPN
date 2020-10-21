import argparse
import pandas as pd
from datetime import datetime

from flask import Flask
from flask import request
from flask import render_template
from flask_socketio import SocketIO,emit

network_segment = "172.16"
client_list = []
subnet_pool = list(range(0, 255))
subnet_table = pd.DataFrame()

app = Flask(__name__)
socketio = SocketIO(app)


@app.route("/")
def socket():
    return "<h1>Signaling Server</h1>"


def list_filter(action):
    if "other" in action:
        return [client for client in client_list if not client==action["other"]]

    elif "to" in  action:
        return [client for client in client_list if client==action["to"]]

    elif "skip" in action:
        return [client for client in client_list if not client==action["skip"]]

    else:
        print_log("list_filter not have this action.")


def client_list_manager(action, socket_id):
    if action == "add":
        client_list.append(socket_id)

    elif action == "del":
        client_list.remove(socket_id)

    else:
        print_log("client_list_manager not have this action.")


def emit_manager(event, *data, **kwargs):
    if kwargs:
        _client_list = list_filter(kwargs)

    if data:
        for socket_id in _client_list:
            emit(event, data[0], room=socket_id)

    else:
        for socket_id in _client_list:
            emit(event, room=socket_id)


def back_to_subnet_pool(socket_id):
    if socket_id in subnet_table.columns:
        subnet_list = list(subnet_table.loc[: ,socket_id])
        subnet_pool.extend(subnet_list)
        subnet_table.drop(columns=[socket_id], inplace=True)
        print_log("{} back to subnet pool.".format(subnet_list))

    if socket_id in subnet_table.index.tolist():
        subnet_list = list(subnet_table.loc[socket_id, :])
        subnet_pool.extend(subnet_list)
        subnet_table.drop(index=[socket_id], inplace=True)
        print_log("{} back to subnet pool.".format(subnet_list))


def print_log(msg):
    now_time = datetime.now()
    print("[{}] {}".format(now_time, msg))


@socketio.on("signaling_connected")
def signaling_connected():
    src_socket_id = request.sid
    client_list_manager("add", src_socket_id)
    print_log("Client {} Connected.".format(src_socket_id))

    emit_data = dict()
    emit_data["src_socket_id"] = src_socket_id
    emit_manager("get_socket_id_from_server", emit_data, to=src_socket_id)
    print_log("Send socketio id to client.")

    if len(client_list) >= 2:
        emit_manager("request_offer_from_server", emit_data, other=src_socket_id)
        print_log("Request offer to client.")


@socketio.on("require_offer_from_client")
def require_offer_from_client(data):
    src_socket_id = request.sid
    dst_socket_id = data["dst_socket_id"]
    pack = data["pack"]

    subnet = str(subnet_pool.pop(0))
    subnet_table.loc[src_socket_id ,dst_socket_id]  = subnet
    network = network_segment + "." + subnet

    emit_data = dict()
    emit_data["src_socket_id"] = src_socket_id
    emit_data["pack"] = pack
    emit_data["pack"]["network"] = network
    print_log("Get offer from client {}.".format(src_socket_id))

    emit_manager("get_offer_from_server", emit_data, to=dst_socket_id)
    print_log("Send offer to client {}.".format(dst_socket_id))


@socketio.on("require_answer_from_client")
def require_answer_from_client(data):
    src_socket_id = request.sid
    dst_socket_id = data["dst_socket_id"]
    pack = data["pack"]

    subnet = subnet_table.loc[dst_socket_id ,src_socket_id]
    network = network_segment + "." + subnet

    emit_data = dict()
    emit_data["src_socket_id"] = src_socket_id
    emit_data["pack"] = pack
    emit_data["pack"]["network"] = network
    print_log("Get answer from client {}.".format(src_socket_id))

    emit_manager("get_answer_from_server", emit_data, to=dst_socket_id)
    print_log("request answer to client {}.".format(dst_socket_id))


@socketio.on("disconnect")
def disconnect():
    socket_id = request.sid
    client_list_manager("del", socket_id)
    back_to_subnet_pool(socket_id)
    print_log("Client {} disconnected.".format(socket_id))


if __name__ == "__main__":
    try:
        print_log("Sockio server started.")
        socketio.run(app, debug=False, host="0.0.0.0", port=9900)
    except:
        print_log("Sockio server start failed.")

