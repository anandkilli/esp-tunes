from machine import Pin, PWM
import time
import os
import json

with open('tonesDict.json', 'r') as tonesDict:
	tones = json.loads(tonesDict.read())

# set up pin PWM timer for output to buzzer or speaker
pwm = PWM(Pin(0)) #D3 on Wemos D1 mini

def playNotes(Val):
	msg = None
	try:
		for i,v in enumerate(Val.split(",")):
			note = tones[v.strip()]
			pwm.duty(512)
			if note == 0:
				pwm.duty(0)
			else:
				pwm.freq(int((note/100)*20)) # change frequency for change tone
				#Taking only 20% of freq as D1 mini (ESP12-E) accepts a maximum of 1 KHz
			time.sleep_ms(150)
		msg = "Done playing"
	except:
		msg = "Something is not right"
	return msg

def startPlay(fileName):
	print("File name receive:", fileName)
	with open(fileName,"r") as tune:
		return playNotes(tune.read())

def receive(sock):
	fragments = []
	chunk = sock.recv(2048)
	chunkStr = str(chunk)
	fragments.append(chunkStr)
	size = None
	if chunkStr.find('size=') > 0:
		#print(chunkStr[chunkStr.find('size=')+5:chunkStr.find('&')])
		size = int(chunkStr[chunkStr.find('size=')+5:chunkStr.find('&',chunkStr.find('size='))])
	recvSize = len(chunk)

	while size and recvSize < size:
		chunk = sock.recv(2048)
		recvSize = recvSize + len(chunk)
		fragments.append(str(chunk))
	return "".join(fragments).replace("'b'","")

def ESPTunesWebserv():
	import socket	
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind(('', 80))
	s.listen(0)	# just queue up some requests

	while True:
		conn, addr = s.accept()
		print("Got a connection from %s" % str(addr))
		request = receive(conn)
		header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
		request = str(request)
		notes = request.find('notes=')
		getSavedTunes = request.find('getSavedTunes')
		saveToFile = request.find('saveToFile')
		playFile = request.find('playFile=')

		if notes > 0 :
			ie = request.find(' ', notes)
			Val = request[notes+6:ie]
			msg = playNotes(Val.replace("%20",""))
			conn.send(header+"{\"status\":\""+msg+"\"}")
		elif getSavedTunes  > 0:
			resp = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"
			fileList = []
			for file in os.listdir():
				if file.endswith(".tune"):
					fileList.append(file)
			resp = resp + "{\"tunes\":["+",".join('"{0}"'.format(w) for w in fileList)+"]}"
			conn.send(resp)
		elif saveToFile > 0:
			fileName = request[request.find("fileName")+9:request.find("&")]
			data = request[request.find("data")+5:request.find(' ', request.find("data"))]
			#print("Request",request)
			#print("Data received:",len(data),"\n",data)
			conn.send(header+"{\"status\":\"success\"}")
			fi = open(fileName+".tune","w")
			fi.write(data)
			fi.close() 
		elif playFile > 0:
			fnameEnd = request.find(' ', playFile)
			fileToPlay = request[request.find("playFile=")+9:fnameEnd]
			msg = startPlay(fileToPlay)
			conn.send(header+"{\"status\":\""+msg+"\"}")
		else:
			with open('esptunes.html', 'r') as html:
				conn.sendall('HTTP/1.1 200 OK\nConnection: close\nServer: WemosD1Mini\nContent-Type: text/html\n\n')
				conn.sendall(html.read())
		conn.sendall('\n')
		conn.close()
		print("Connection wth %s closed" % str(addr))



