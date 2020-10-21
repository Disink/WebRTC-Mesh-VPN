import sys
import asyncio

from pyroute2 import IPRoute

from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.signaling import object_to_string, object_from_string

import tuntap


class WebRTCVPN:
    def __init__(self):
        self.pc =  RTCPeerConnection()
        self.channel = None

    async def create_offer(self):
        channel = self.pc.createDataChannel("chat")
        self.channel = channel

        await self.pc.setLocalDescription(await self.pc.createOffer())

        return object_to_string(self.pc.localDescription)

    async def create_answer(self, offer):
        offer = object_from_string(offer)

        await self.pc.setRemoteDescription(offer)
        await self.pc.setLocalDescription(await self.pc.createAnswer())

        @self.pc.on("datachannel")
        def on_datachannel(channel):
            self.channel = channel

        return object_to_string(self.pc.localDescription)

    async def set_answer(self, answer):
        answer = object_from_string(answer)
        await self.pc.setRemoteDescription(answer)

    def get_channel(self):
        return self.channel

    def get_pc(self):
        return self.pc

    def create_tuntap(self, name, address, mtu, channel):
        self.tap = tuntap.Tun(name=name)
        self.tap.open()

        #channel.on("message")(self.tap.fd.write)
        @channel.on("message")
        def on_message(message):
            self.tap.fd.write(message)

        def tun_reader():
            data = self.tap.fd.read(self.tap.mtu)
            channel_state = self.channel.transport.transport.state

            if data and channel_state == "connected":
                channel.send(data)

        loop = asyncio.get_event_loop()
        loop.add_reader(self.tap.fd, tun_reader)

        self.tap.up()

        ip = IPRoute()
        index = ip.link_lookup(ifname=name)[0]
        ip.addr('add', index=index, address=address, mask=24)
        ip.link("set", index=index, mtu=mtu)

    def set_route(self, dst, gateway):
        ip = IPRoute()
        ip.route('add', dst=dst, gateway=gateway)

    async def input(self):
        loop = asyncio.get_event_loop()

        reader = asyncio.StreamReader(loop=loop)
        read_pipe = sys.stdin
        read_transport, _ = await loop.connect_read_pipe(
            lambda: asyncio.StreamReaderProtocol(reader), read_pipe
        )

        data = await reader.readline()

        return data.decode(read_pipe.encoding)

    async def hold(self):
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader(loop=loop)
        data = await reader.readline()

        return data

    async def monitor(self):
        loop = asyncio.get_event_loop()
        while True:
            if not self.channel == None:
                if self.channel.transport.transport.state == "closed":
                    loop.run_until_complete(self.pc.close())
                    self.tap.close()
                    break
            await asyncio.sleep(1)

        return "closed"
