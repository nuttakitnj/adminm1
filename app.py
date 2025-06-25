from flask import Flask, render_template_string,render_template,request
from flask_mqtt import Mqtt
from flask_socketio import SocketIO, emit, join_room
import eventlet
import pymysql
import re
import subprocess


eventlet.monkey_patch()  # patch for eventlet async support

app = Flask(__name__)

# Connect to MySQL
connection = pymysql.connect(
    host='203.151.166.53',
    user='mdbiot_remote_php',
    password='Asefa@2o23',
    db='mdbiot_com',
    cursorclass=pymysql.cursors.DictCursor
)

app.config['MQTT_BROKER_URL'] = 'mqtt.mdbiot.com'  # public broker
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_USERNAME'] = ''  # set if needed
app.config['MQTT_PASSWORD'] = ''  # set if needed
app.config['MQTT_KEEPALIVE'] = 60
app.config['MQTT_TLS_ENABLED'] = False

mqtt = Mqtt(app)

# Subscribe topic
SUBSCRIBE_TOPIC = 'meow/test_sub'
socketio = SocketIO(app, cors_allowed_origins='*')

messages = []
subscribed_topics = set()

# Callback: when MQTT client connects to broker
@mqtt.on_connect()
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    mqtt.subscribe(SUBSCRIBE_TOPIC)

# Callback: when a message arrives on subscribed topics
@mqtt.on_message()
def on_message(client, userdata, message):
    msg = message.payload.decode()
    topic = message.topic
    print(f"[MQTT] {topic}: {msg}")
    socketio.emit('mqtt_message', {'topic': topic, 'message': msg})
    # print(f"Received message on {message.topic}: {message.payload.decode()}")

@app.route('/')
def index():
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM device_status WHERE device_SN LIKE 'M1%'")
            result = cursor.fetchall()
            d_arr = [item['device_SN']  for item  in result]
            # Filter values starting with "M1"
            pattern = r'^M1'  # regex: start with M1
            # print(sorted_people.)
            matched_sns = [sn for sn in d_arr if re.match(pattern, sn)]
            sorted_people = sorted(result, key=lambda person: person["device_SN"])

            return render_template('index.html',data = matched_sns,data_arr=sorted_people )
        return render_template('index.html') 
        
    except Exception as e:
        print('Except as {}'.format(e))
        return render_template('index.html') 

# @app.route('/mqtt', methods=['GET', 'POST'])
# def debug_device():
#     mqtt.subscribe('meow/#')


@app.route('/mqtt', methods=['GET', 'POST'])
def mx_mqtt():
    message = None
    subTopic=""
    if request.method == 'POST':
        data = request.get_json()
        subTopic = data.get("subTopic")
    topic = request.form.get('topic')
    device_sn = request.args.get('device_sn')
    cmd_on = '{ "mode": "cmd", "data":{"VPN":1}, "cmd_id": "C1728370820091" }'
    cmd_off = '{ "mode": "cmd", "data":{"VPN":0}, "cmd_id": "C1728370820091" }'
    cmd_check = '{ "mode": "cmd", "data":{"VPN":2}, "cmd_id": "C1728370820091" }'
    # print(device_sn,topic)

    return render_template('mx_mqtt.html', message=device_sn,topic=topic,cmd_on=cmd_on,cmd_off=cmd_off,cmd_check=cmd_check)




@socketio.on('subscribe')
def handle_subscribe(data):
    topic = data.get('topic')
    print("==",topic)
    if topic and topic not in subscribed_topics:
        mqtt.subscribe(topic)
        subscribed_topics.add(topic)
        print(f"Subscribed to topic: {topic}")
        socketio.emit('mqtt_topic', {'topic': topic, 'message': f"✅ Subscribed to {topic}"})
    else:
        socketio.emit('mqtt_topic', {'topic': topic, 'message': f"⚠️ Already subscribed to {topic}"})

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    topic = data.get('topic')
    print("==",topic)
    if topic and topic in subscribed_topics:
        mqtt.unsubscribe(topic)
        print(subscribed_topics)
        subscribed_topics.remove(topic)
        print(f"Subscribed to topic: {topic}")
        socketio.emit('mqtt_topic', {'topic': topic, 'message': f"✅ Subscribed to {topic}"})
    else:
        socketio.emit('mqtt_topic', {'topic': topic, 'message': f"⚠️ Already subscribed to {topic}"})

@socketio.on('sendCMD')
def sendCMD(data):
    send_topic = data.get('send_topic')
    send_message = data.get('send_message')
    mqtt.publish(send_topic, send_message)
    print(f"[PUBLISH] {send_topic} → {send_message}")
    socketio.emit('mqtt_sendCMD', {'topic': send_topic, 'message': f"✅ Send command to {send_message}"})

@socketio.on('openVNC')
def openVNC(data):
    send_message = data.get('send_message')
    print(send_message)
    # Replace with your VNC address and port
    vnc_address = "{}::5900".format(send_message)  # or "192.168.1.100::5901" for some clients
    
    # Example for RealVNC Viewer
    subprocess.Popen(["C:\\Program Files\\RealVNC\\VNC Viewer\\vncviewer.exe", vnc_address])

@socketio.on('connectVPN')
def connectVPN(data):
    # Use GUI-based OpenVPN
    subprocess.run([
        r"C:\Program Files\OpenVPN\bin\openvpn-gui.exe",
        "--connect", "VPN.ovpn"
    ])
  
@socketio.on('closeVPN')
def closeVPN(data):
    subprocess.run(["taskkill", "/IM", "openvpn.exe", "/F"])  

@socketio.on('openSSH')
def closeSSH(data):
    send_message = data.get('send_message')
    print(send_message)
    hostname = "mdbcare@{}".format(send_message)
    subprocess.run(["start", "cmd", "/k", f"ssh {hostname}"], shell=True)
 
@socketio.on('testMSG')
def testMSG(data):
    send_topic = data.get('send_topic')
    send_message = data.get('send_message')
    # send_message = '{ "mode": "cmd", "data":{"EV000003":{"offset_time":{"read":1}}}, "cmd_id": "C1728370820091" }'
    # send_message = '{ "mode": "cmd", "data":{"EV000003":{"offset_time":{"read":1}}}, "cmd_id": "C1728370820091" }'
    mqtt.publish(send_topic, send_message)
    print(f"[PUBLISH] {send_topic} → {send_message}")
    socketio.emit('mqtt_sendCMD2', {'topic': send_topic, 'message': f"✅ Send command to {send_message}"})

# for WebRTC
@app.route('/testWebRTC')
def testWebRTC():
    return render_template('test_webrtc.html')

@socketio.on('join')
def handle_join(room):
    join_room(room)
    print(f"User joined room: {room}")

@socketio.on('offer')
def handle_offer(data):
    emit('offer', {'offer': data['offer']}, room=data['room'], include_self=False)

@socketio.on('answer')
def handle_answer(data):
    emit('answer', {'answer': data['answer']}, room=data['room'], include_self=False)

@socketio.on('ice-candidate')
def handle_ice(data):
    emit('ice-candidate', {'candidate': data['candidate']}, room=data['room'], include_self=False)



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)