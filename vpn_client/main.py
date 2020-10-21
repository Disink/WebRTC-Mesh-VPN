import socketio
import argparse
import asyncio
import nest_asyncio
from datetime import datetime

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import object_to_string, object_from_string

from webrtc_vpn import WebRTCVPN

nest_asyncio.apply()

rtc_list = {}
mtu = 1400
debug_mode = False


def print_log(msg, *args):
    now_time = datetime.now()
    print("[{}] {}".format(now_time, msg))


def print_debug_log(msg, *args):
    if debug_mode == True:
        now_time = datetime.now()
        print("[{}] {}".format(now_time, msg))


def on_socketio(socketio, args):
    loop = asyncio.get_event_loop()

    @socketio.on("request_offer_from_server")
    def request_offer_from_server(data):
        src_socket_id = data["src_socket_id"]
        print_debug_log("Request offer from client {}.".format(src_socket_id))

        rtc_list[src_socket_id] = WebRTCVPN()
        rtc= rtc_list[src_socket_id]
        offer = loop.run_until_complete(rtc_list[src_socket_id].create_offer())

        emit_data = dict()
        emit_data["dst_socket_id"] = src_socket_id

        emit_data["pack"] = dict()
        emit_data["pack"]["offer"] = offer
        emit_data["pack"]["peer_name"] = args.name
        emit_data["pack"]["route"] = args.route

        socketio.emit("require_offer_from_client", emit_data)
        print_debug_log("Require offer to client {}.".format(src_socket_id))

    @socketio.on("get_offer_from_server")
    def get_offer_from_server(data):
        src_socket_id = data["src_socket_id"]
        offer = data["pack"]["offer"]
        peer_name = data["pack"]["peer_name"]
        network = data["pack"]["network"]
        route_list = data["pack"]["route"]
        print_debug_log("Get offer from client {}.".format(src_socket_id))

        rtc_list[src_socket_id] = WebRTCVPN()
        rtc= rtc_list[src_socket_id]
        answer = loop.run_until_complete(rtc_list[src_socket_id].create_answer(offer))

        emit_data = dict()
        emit_data["dst_socket_id"] = src_socket_id

        emit_data["pack"] = dict()
        emit_data["pack"]["answer"] = answer
        emit_data["pack"]["peer_name"] = args.name
        emit_data["pack"]["route"] = args.route

        socketio.emit("require_answer_from_client", emit_data)
        print_debug_log("Send answer to client {}.".format(src_socket_id))

        name = "tun-{}".format(peer_name)
        local_address = "{}.{}".format(network, "2")
        peer_address = "{}.{}".format(network, "1")

        pc = rtc.get_pc()

        @pc.on("datachannel")
        def on_datachannel(channel):
            print_log("VPN channel connected.")

            rtc.create_tuntap(name, local_address, mtu, channel)
            print_log("Create new TUN/TAP.")
            print_msg = "Name: {} Local_adderss: {} Peer_address: {} MTU: {}."
            print_log(print_msg.format(name, local_address, peer_address, mtu))

            if not route_list == None:
                print_log("Add new route.")
                for route in route_list:
                    rtc.set_route(route, peer_address)
                    print_log("Network: {} Dst: {}.".format(route, peer_address))

        channel_state = loop.run_until_complete(rtc_list[src_socket_id].monitor())

        print_log("VPN channel closed.")
        print_log("Remove new TUN/TAP.")
        print_msg = "Name: {} Local_adderss: {} Peer_address: {} MTU: {}."
        print_log(print_msg.format(name, local_address, peer_address, mtu))

        del rtc_list[src_socket_id]

    @socketio.on("get_answer_from_server")
    def get_answer_from_server(data):
        src_socket_id = data["src_socket_id"]
        answer = data["pack"]["answer"]
        peer_name = data["pack"]["peer_name"]
        network = data["pack"]["network"]
        route_list = data["pack"]["route"]
        print_debug_log("Get answer from client {}.".format(src_socket_id))

        rtc = rtc_list[src_socket_id]
        loop.run_until_complete(rtc_list[src_socket_id].set_answer(answer))

        name = "tun-{}".format(peer_name)
        local_address = "{}.{}".format(network, "1")
        peer_address = "{}.{}".format(network, "2")

        channel = rtc.get_channel()

        @channel.on("open")
        def on_open():
            print_log("VPN channel connected.")

            rtc.create_tuntap(name, local_address, mtu, channel)
            print_log("Create new TUN/TAP.")
            print_msg = "Name: {} Local_adderss: {} Peer_address: {} MTU: {}."
            print_log(print_msg.format(name, local_address, peer_address, mtu))

            if not route_list == None:
                print_log("Add new route.")
                for route in route_list:
                    rtc.set_route(route, peer_address)
                    print_log("Network: {} Dst: {}.".format(route, peer_address))

        channel_state = loop.run_until_complete(rtc_list[src_socket_id].monitor())

        print_log("VPN channel closed.")
        print_log("Remove new TUN/TAP.")
        print_msg = "Name: {} Local_adderss: {} Peer_address: {} MTU: {}."
        print_log(print_msg.format(name, local_address, peer_address, mtu))

        del rtc_list[src_socket_id]


    @socketio.on("get_socket_id_from_server")
    def get_socketid_id_from_server(data):
        src_socket_id = data["src_socket_id"]
        print_debug_log("Socketio id: {}".format(src_socket_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Webrtc mesh VPN")
    parser.add_argument("--name", "-n", type=str, required=True, help="Peer name")
    parser.add_argument("--server", "-s", type=str, required=True, help="Signaling server address")
    parser.add_argument("--route", "-r", type=str, action='append', help="push route to peer")

    args = parser.parse_args()

    socketio = socketio.Client()

    on_socketio(socketio, args)

    try:
        server = "http://" + args.server
        socketio.connect(server)
        print_log("Connected to socketio server.")

        socketio.emit("signaling_connected")
    except:
        print_log("Connect to socketio server failed.")

