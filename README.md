# WebRTC Mesh VPN
使用```WebRTC```讓多個客戶端可以簡單與快速的建立起Mesh VPN, 有別於一般的VPN, 在兩點建立VPN時, Server端必須擁有實體IP, 而使用```WebRTC```技術只需要一個實體IP, 就可以達成數十甚至數百個客戶端的複雜Mesh Netwrok.

# 需要什麼?
- STUN Server (使用Google提供的STUN Server)
- Signaling Server (需要一個實體IP)
- VPN Client (兩個或以上的客戶端)

# 如何運作?
兩個客戶端連入```Signaling Server```時, 客戶端會向```STUN Server```請求```SDP```, 並透過```Signaling Server```交換, 用於建立```RTC connection```, 最後建立```TUN/TAP```完成P2P VPN, 當更多客戶端連入```Signaling Server```時, 會自動與所有客戶端建立起P2P VPN, 進而形成Mesh Network.

# Signaling Server
使用```flask_socketio```來實現伺服器與客戶端雙向通訊, 用於交換來自客戶端的```SDP```與```TUN/TAP address``` ```Route```...等資訊.

## 安裝
```
pip install flask
pip install flask_socketio
pip install eventlet
pip install pandas
```

## 執行
```
python ./main.py
```

# VPN Client
使用```AioRTC```來實現```WebRTC```的功能, 並使用```python-socketio```實現與伺服器的雙向溝通, 交換```SDP```與```TUN/TAP address``` ```Route```…等資訊, 來建立```RTC connection```與```TUN/TAP```.

## 安裝
```
pip install aiortc
pip install python-socketio
pip install python-socketio[client]
pip install nest_asyncio
pip install pyroute2
```

## 執行
```
python ./vpn_client.py -n home -s 0.0.0.0:9900 -r 192.168.10.0/24 -r 192.168.11.0/24
```
```
-n --name [peer_name]
    用其他客戶端建立TUN/TAP命名時使用(例:tun-home)
-s --server [ip:port]
    Signaling Server的IP與Port(預設使用9900)
-r --route [netwrok/netmask]
    有額外Route時使用, 將自動推送到其他客戶端
```
