#!/usr/bin/python
# -*- coding: latin-1 -*-

### BEGIN LICENSE
# Copyright (c) 2016 Jpnos <jpnos@gmx.com>

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
### END LICENSE

                                                                         
###### Core Imports ###############################################################################                                                        

import threading
import os, os.path, sys
import time
import sqlite3
#import urllib2
import random
from math import cos, sin, pi
import datetime
import time
import json
import socket
import re
from requests import get
import locale
locale.setlocale(locale.LC_ALL, '')
from threading import Thread
from functools import partial
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import logging
import webbrowser

######  Kivy Imports ##############################################################################
import kivy

kivy.require('1.9.0')  # replace with your current kivy version !

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SwapTransition
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.storage.jsonstore import JsonStore
from kivy.uix.label import Label
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout

Builder.load_file('kv/boot.kv')
Builder.load_file('kv/main.kv')
Builder.load_file('kv/min.kv')
Builder.load_file('kv/meteo.kv')
Builder.load_file('kv/summer.kv')

    
###### Other Imports ##############################################################################

import cherrypy
import schedule
import certifi
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
http = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=certifi.where(),
    timeout=urllib3.Timeout(connect=1.0, read=2.0))

settings = JsonStore("./setting/thermostat_settings.json")
state = JsonStore("./setting/thermostat_state.json")

#####Framework Telegram
if settings.get("telegram")["enabled"] == 1:
    import telepot
    from telepot.loop import MessageLoop
    telegramTimeout = 60 if not (settings.exists("thermostat")) else settings.get("telegram")["timeout"]
    testTimeout = 0
    chatIdTest = 0


###### Logging ####################################################################################
logging.basicConfig(filename='./log/logging.log',level=logging.DEBUG)
#for key in logging.Logger.manager.loggerDict:
#    print(key)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.CRITICAL)

###### Thermostat persistent settings #############################################################

THERMOSTAT_VERSION = "5.1.0"

# Debug settings

debug = False
useTestSchedule = False

# Threading Locks

thermostatLock = threading.RLock()
weatherLock = threading.Lock()
scheduleLock = threading.RLock()

##############################################################################
#                                                                            #
#       GPIO & Simulation Imports                                            #
#                                                                            #
##############################################################################

try:
    import RPi.GPIO as GPIO
    print ("Rpi used w1")
except ImportError:
    import FakeRPi.GPIO as GPIO
    print("No RPI used")
try:
    from Adafruit_BME280 import *
    sensor = BME280(t_mode=BME280_OSAMPLE_8, p_mode=BME280_OSAMPLE_8, h_mode=BME280_OSAMPLE_8)
    print ("BMP used..")
except:
    print("No BMP used..")
    
from w1thermsensor import W1ThermSensor    
###### Utility Class switch #######################################################################

class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False

    
###### Inizializzo il log #########################################################################
###### MySensor.org Controller compatible translated constants ####################################

MSG_TYPE_SET = "set"
MSG_TYPE_PRESENTATION = "presentation"
CHILD_DEVICE_NODE = "node"
CHILD_DEVICE_UICONTROL_HEAT = "heatControl"
CHILD_DEVICE_UICONTROL_COOL = "coolControl"
CHILD_DEVICE_UICONTROL_HOLD = "holdControl"
CHILD_DEVICE_WEATHER_FCAST_TODAY = "weatherForecastToday"
CHILD_DEVICE_WEATHER_FCAST_TOMO = "weatherForecastTomorrow"
CHILD_DEVICE_WEATHER_CURR = "weatherCurrent"
CHILD_DEVICE_HEAT = "heat"
CHILD_DEVICE_COOL = "cool"
CHILD_DEVICE_PIR = "motionSensor"
CHILD_DEVICE_TEMP = "temperatureSensor"
CHILD_DEVICE_SCREEN = "screen"
CHILD_DEVICE_SCHEDULER = "scheduler"
CHILD_DEVICE_WEBSERVER = "webserver"
CHILD_DEVICE_DHTIN = "DhtIn"
CHILD_DEVICE_DHTOUT = "DhtOut"
CHILD_DEVICE_DHTIR = "DhtIr"
CHILD_DEVICE_DHTZONE = "DhtZone"
CHILD_DEVICE_DHTRELE = "DhtRele"
CHILD_DEVICE_DHTCLEAR = "Clear_dht"

CHILD_DEVICES = [
    CHILD_DEVICE_NODE,
    CHILD_DEVICE_UICONTROL_HEAT,
    CHILD_DEVICE_UICONTROL_COOL,
    CHILD_DEVICE_UICONTROL_HOLD,
    CHILD_DEVICE_WEATHER_CURR,
    CHILD_DEVICE_WEATHER_FCAST_TODAY,
    CHILD_DEVICE_WEATHER_FCAST_TOMO,
    CHILD_DEVICE_HEAT,
    CHILD_DEVICE_COOL,
    CHILD_DEVICE_PIR,
    CHILD_DEVICE_TEMP,
    CHILD_DEVICE_SCREEN,
    CHILD_DEVICE_SCHEDULER,
    CHILD_DEVICE_WEBSERVER,
    CHILD_DEVICE_DHTIN,
    CHILD_DEVICE_DHTOUT,
    CHILD_DEVICE_DHTIR,
    CHILD_DEVICE_DHTZONE,
    CHILD_DEVICE_DHTRELE,
    CHILD_DEVICE_DHTCLEAR
]

CHILD_DEVICE_SUFFIX_UICONTROL = "Control"

MSG_SUBTYPE_NAME = "sketchName"
MSG_SUBTYPE_VERSION = "sketchVersion"
MSG_SUBTYPE_BINARY_STATUS = "binaryStatus"
MSG_SUBTYPE_TRIPPED = "armed"
MSG_SUBTYPE_ARMED = "tripped"
MSG_SUBTYPE_TEMPERATURE = "temperature"
MSG_SUBTYPE_FORECAST = "forecast"
MSG_SUBTYPE_CUSTOM = "custom"
MSG_SUBTYPE_TEXT = "text"
MSG_SUBTYPE_DHT = "DhtWifi"


LOG_FILE_NAME = "./log/thermostat.log"

LOG_ALWAYS_TIMESTAMP = True

LOG_LEVEL_DEBUG = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_ERROR = 3
LOG_LEVEL_STATE = 4
LOG_LEVEL_NONE = 5

LOG_LEVELS = {
    "debug": LOG_LEVEL_DEBUG,
    "info": LOG_LEVEL_INFO,
    "state": LOG_LEVEL_STATE,
    "error": LOG_LEVEL_ERROR
}

LOG_LEVELS_STR = {v: k for k, v in LOG_LEVELS.items()}

logFile = None


def log_dummy(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    pass


def log_file(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    if level >= logLevel:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z ")
        logFile.write(
            ts + LOG_LEVELS_STR[level] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg + "\n")


def log_(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    if level >= logLevel:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z ") if LOG_ALWAYS_TIMESTAMP or timestamp else ""
        (ts + LOG_LEVELS_STR[level] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg)


loggingChannel = "none" if not (settings.exists("logging")) else settings.get("logging")["channel"]
loggingLevel = "state" if not (settings.exists("logging")) else settings.get("logging")["level"]

for case in switch(loggingChannel):
    if case('none'):
        log = log_dummy
        break
    if case('file'):
        log = log_file
        logFile = open(LOG_FILE_NAME, "a", 0)
        break
    if case(''):
        log = log_
        break
    if case():  # default
        log = log_dummy

logLevel = LOG_LEVELS.get(loggingLevel, LOG_LEVEL_NONE)

# Send presentations for Node

log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_NAME, "Thermostat Starting Up...", msg_type=MSG_TYPE_PRESENTATION)
log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_VERSION, THERMOSTAT_VERSION, msg_type=MSG_TYPE_PRESENTATION)

# send presentations for all other child "sensors"

for i in range(len(CHILD_DEVICES)):
    child = CHILD_DEVICES[i]
    if child != CHILD_DEVICE_NODE:
        log(LOG_LEVEL_STATE, child, child, "", msg_type=MSG_TYPE_PRESENTATION)
###### Inizializzo pin/variabili di controllo rasp ################################################

elevation = 0 if not (settings.exists("thermostat")) else settings.get("calibration")["elevation"]
boilingPoint = (100.0 - 0.003353 * elevation)
freezingPoint = 0.01
referenceRange = boilingPoint - freezingPoint
correctSensor = 0 if not (settings.exists("thermostat")) else settings.get("calibration")["correctSensor"]
tempHysteresis = 0.5 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempHysteresis"]
tempScale = settings.get("scale")["tempScale"]
windFactor = 3.6 if tempScale == "metric" else 1.0
windUnits = " km/h" if tempScale == "metric" else " mph"
sensorUnits = W1ThermSensor.DEGREES_C if tempScale == "metric" else W1ThermSensor.DEGREES_F
boilingMeasured = settings.get("calibration")["boilingMeasured"]
freezingMeasured = settings.get("calibration")["freezingMeasured"]
measuredRange = boilingMeasured - freezingMeasured

heatPin = 27 if not (settings.exists("thermostat")) else settings.get("thermostat")["heatPin"]
lightPin = 24 if not (settings.exists("thermostat")) else settings.get("thermostat")["lightPin"]
coolPin = 26 if not (settings.exists("thermostat")) else settings.get("thermostat")["coolPin"]

csvSaver = None
minScreen = None

GPIO.setmode(GPIO.BCM)
GPIO.setup(heatPin, GPIO.OUT)
GPIO.output(heatPin, GPIO.HIGH)
GPIO.setup(lightPin, GPIO.OUT)
GPIO.output(lightPin, GPIO.HIGH)
GPIO.setup(coolPin, GPIO.OUT)
GPIO.output(coolPin, GPIO.HIGH)

tempSensor = None
try:
    tempSensor = W1ThermSensor()
    print ("tempsensor W1 ON")
except:
    print ("tempsensor W1 OFF")
try:
    sensor = BME280(t_mode=BME280_OSAMPLE_8, p_mode=BME280_OSAMPLE_8, h_mode=BME280_OSAMPLE_8)
    tempSensor = "bmp280"
    print ("tempsensor BMP280 ON")
except:
    print ("tempsensor BMP280 OFF")

# PIR (Motion Sensor) setup:

pirEnabled = 0 if not (settings.exists("pir")) else settings.get("pir")["pirEnabled"]
pirPin = 5 if not (settings.exists("pir")) else settings.get("pir")["pirPin"]

pirCheckInterval = 0.5 if not (settings.exists("pir")) else settings.get("pir")["pirCheckInterval"]

pirIgnoreFromStr = "00:00" if not (settings.exists("pir")) else settings.get("pir")["pirIgnoreFrom"]
pirIgnoreToStr = "00:00" if not (settings.exists("pir")) else settings.get("pir")["pirIgnoreTo"]

pirIgnoreFrom = datetime.time(int(pirIgnoreFromStr.split(":")[0]), int(pirIgnoreFromStr.split(":")[1]))
pirIgnoreTo = datetime.time(int(pirIgnoreToStr.split(":")[0]), int(pirIgnoreToStr.split(":")[1]))

if pirEnabled:
    GPIO.setup(pirPin, GPIO.IN)
    

###### Inizializzo Database in memoria ############################################################
if state.exists("state"):
    dati_lavoro =[(0,18.0,state.get("state")["NoIce"],state.get("state")["setTemp"],state.get("state")["Programma"],state.get("state")["Stato"],state.get("state")["ManualTemp"],0,1)]
else :
    dati_lavoro = [(0,18.0,16.0, 16.0,1,1,18,0,1)]

con = sqlite3.connect(":memory:", check_same_thread = False)

###Creo table data ################################################################################
### 0 = Id = identificativo
### 1 = Caldaia/Condizionatore = stato rele accensione Caldaia 0 = OFF ; 1 = ON
### 2 = Noice = Temperatura Noice
### 3 = SetTemp = Temperatura Configurata da raggiungere
### 4 = Temp = Temperatura letta e di riferimento
### 5 = Umidita = Umidita rilevata da sensori interni
### 6 = Pressione = Pressione rilevata da sensori Interni
### 7 = ProgSistema = Programma Sistema Generale 0 = Spento ; 1 = Inverno/Riscaldamento ; 2 = Estate/Condizionamento 
### 8 = StatoSistema = Stato Configurato 0 = OFF ; 1 = Auto; 2= Manuale; 3=NoIce
### 9 = Tout = Temperatura Esterna
### 10 = ManTemp = Temperatura da mantenere in manuale
### 11 = SummerTemp = Temperatura da mantenere in Estate
### 12 = Switch = Inizio 1 - Fine 0 per calcolare controllo climatico
### 13 = Meteo ora di lettura dei dati meteo

con.execute("CREATE TABLE data(Id integer,Caldaia integer, NoIce real ,SetTemp real ,Temp real,Umidita real,Pressione real,ProgSistema integer,StatoSistema integer ,Tout real,ManTemp real,SummerTemp real,Switch integer,Meteo real)")
con.executemany("INSERT INTO data(Caldaia,Temp,NoIce,SetTemp,ProgSistema,StatoSistema,ManTemp,Meteo,Id) values (?,?,?,?,?,?,?,?,?)", dati_lavoro)


###Creo table periferiche dht #########################################################################
### 0 = Id = Identificativo
### 1 = Nome = Nome periferica
### 2 = Ip = Ip periferica
### 3 = TempLetta = Temperatura letta da DHT
### 4 = UmiditaLetta = Umidita Letta da DHT
### 5 = PressioneLetta = Pressione Letta da DHT
### 6 = setTemp = Temperatura da Impostare per i DHT
### 7 = TipoDht = Tipo di DHT 0 = temp ext ; 1 = Rele ; 2 = dati completi  ; 3 = Solo Visualizzazione
### 8 = Progressivo = 0 valore Aggiornato da DHT ogni altro numero fino a x vuol dire che non si aggiorna il DHT a 10 lo cancello
### 9 = StatoDht = 0 temperatura raggiunta 1 Temperatura da raggiungere
### 10 = StatoSistema = 0 = spento ; 1 =  acceso ; 
con.execute("CREATE TABLE periferiche(Id text,Nome text,Ip text,TempLetta real,UmiditaLetta real,PressioneLetta real,SetTemp real,TipoDht integer,StatoDht integer,StatoSistema integer,Progressivo integer)")
for c in range(1,12):
    #if c<6:
        #d = c
    #elif c>5 and c<12:
        #d = c/2
    d=random.randint(2, 3)
    p= random.randint(16, 28)
    t = random.randint(16, 28)
    table_dht=[(c,"test"+str(c),"192.168.1.1",p,45.0,1021,t,0,d,0,0)]
    con.executemany("insert into periferiche(Id ,Nome ,Ip ,TempLetta ,UmiditaLetta ,PressioneLetta ,SetTemp ,Progressivo ,TipoDht ,StatoDht,StatoSistema ) values (?,?,?,?,?,?,?,?,?,?,?)",table_dht)

###Creo table periferiche rele #########################################################################
### 0 = Id = Identificativo
### 1 = Nome = Nome periferica
### 2 = Ip = Ip periferica
### 3 = Versione = Numero rele - max 8
### 4 = Bitmap = Valore dei rele 

con.execute("CREATE TABLE rele(Id text,Nome text,Ip text,Versione real,Bitmap text)")

###### creo tabella dati temperatura ##############################################################
con.execute("CREATE TABLE temptable(data integer,temp real)")

                
######  test delle pagine  ########################################################################
def change(dt):
    con.execute("DELETE FROM periferiche WHERE Progressivo >8")
    con.execute("UPDATE periferiche SET Progressivo = Progressivo +1")

    
###### Routine lettura Temperatura ################################################################

def check_sensor_temp(dt):
    with thermostatLock:
        global tempSensor,sensor
        # tempSensor,sensorUnits
        #correctedTemp = 18
        if tempSensor is not None:
            if tempSensor == "bmp280":
                rawTemp = round(sensor.read_temperature(),1)
                hectopascals = sensor.read_pressure() / 100
                humidity = sensor.read_humidity()
                #print rawTemp
            else:
                rawTemp = round(tempSensor.get_temperature(sensorUnits),1)
            #print rawTemp
            correctedTemp = round((((rawTemp - freezingMeasured) * referenceRange) / measuredRange) + freezingPoint + correctSensor,1)
            data_main = con.execute("select * from data where Id == 1")
            for row in data_main.fetchall():
                priorCorrected = row[4]
            #print correctedTemp,priorCorrected
            if tempSensor == "bmp280":
                con.execute("UPDATE data SET Temp = ?, Umidita = ?, Pressione = ? WHERE ID = ?",(correctedTemp,humidity,hectopascals,1))
            else:
                con.execute("UPDATE data SET Temp = ? WHERE ID = ?",(correctedTemp,1))
            tabellaTemp(correctedTemp)
        data_main = con.execute("SELECT * FROM data WHERE Id == 1")
        for row in data_main.fetchall():
            if (row[8] > 0):
                change_system_settings()
            else:
                if (state.get("state")["Stato"] > 0):
                    change_system_settings()
                    
###### Routine di servizio ########################################################################

def tabellaTemp(temp):
    #print datetime.datetime.now(),(datetime.datetime.now() - datetime.timedelta(seconds=300))
    con.execute("INSERT INTO temptable(data,temp) VALUES(?,?)",(datetime.datetime.now(),temp))
    con.execute("DELETE FROM temptable WHERE data <= '"+ str((datetime.datetime.now() - datetime.timedelta(seconds=150))) + "'")
        
def salvaTempiTemp():
    file_name = "./log/" + "switchTemp.csv"
    out_file = open(file_name, "a")
    data_temper = con.execute("SELECT * FROM data WHERE Id == 1")
    for row in data_temper.fetchall():
        out_file.write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ", " + str(row[3]) + ", " + str(
        row[4]) + ", " + str(row[9]) + ","+str(row[12])+"\n")
    out_file.close()
    
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(10)  # 10 seconds
    try:
        s.connect(("8.8.8.8", 80))  # Google DNS server
        ip = s.getsockname()[0]
        log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/ip", ip, timestamp=False)
    except socket.error:
        ip = "127.0.0.1"
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/ip",
            "FAILED to get ip address, returning " + ip, timestamp=False)

    return ip    
###### Routine aggiorna GPIO sistema  e dht #######################################################

def change_system_settings():
    with thermostatLock:
        ### Test porte aperte #########
        try:
            test_temp = 10000
            testa = 0
            test_main = con.execute("SELECT * FROM temptable")
            for row in test_main.fetchall():
                if test_temp == 10000:
                    test_temp = row[1]
                else:
                    testa = testa +(test_temp - row[1]) 
                    test_temp = row[1]
        except:
            test_temp = 0
        data_main = con.execute("SELECT * FROM data WHERE Id == 1")
        for row in data_main.fetchall():
            #print row
            setT = row[3]
            temp = row[4]
            noIce = row[2]
            programma = row[7]
            stato = row[8]
            manTemp = row[10]
            caldaia_pre = row[1]
            summer = row[11]
        dht_main = con.execute("SELECT * FROM periferiche WHERE TipoDht == 2")
        statoDht = 0
        for row in dht_main:
            ## row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9]
            if row[9] == 1:
                statoDht = 1
        if programma == 1 and stato == 1:
            if setT >= temp + tempHysteresis or statoDht == 1:
                GPIO.output(heatPin, GPIO.LOW)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(1,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(1,5))
            elif setT < temp :
                GPIO.output(heatPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(0,5))
        elif programma ==1 and stato == 3 :
            if noIce >= temp + tempHysteresis  or statoDht == 1:
                GPIO.output(heatPin, GPIO.LOW)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(1,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(1,5))
            elif noIce < temp :
                GPIO.output(heatPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(0,5))
        elif programma == 1 and stato == 2:
            if manTemp >= temp + tempHysteresis or statoDht == 1:
                GPIO.output(heatPin, GPIO.LOW)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(1,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(1,5))
            elif manTemp < temp :
                GPIO.output(heatPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(0,5))
        elif programma == 2 and stato == 1:
            if setT <= temp + tempHysteresis or statoDht == 1:
                GPIO.output(coolPin, GPIO.LOW)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(1,1))
            elif setT > temp :
                GPIO.output(coolPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
        elif programma == 2 and stato == 2:
            if manTemp <= temp + tempHysteresis or statoDht == 1:
                GPIO.output(coolPin, GPIO.LOW)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(1,1))
            elif manTemp > temp :
                GPIO.output(coolPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
        else :
                GPIO.output(heatPin, GPIO.HIGH)
                GPIO.output(coolPin, GPIO.HIGH)
                con.execute("UPDATE data SET Caldaia = ? WHERE Id = ?",(0,1))
                con.execute("UPDATE periferiche SET StatoDht = ? WHERE TipoDht = ?",(0,5))
        #### Salviamo tutto cosi recuperiamo in avvio #####
        data_main = con.execute("SELECT * FROM data WHERE Id == 1")
        for row in data_main.fetchall():
            if caldaia_pre <> row[1]:
                save_graph(0.5)
                aggiornaDht(0.1)
                save_state()
                if row[1] == 0 and row[12] == 1:
                        con.execute("UPDATE data SET Switch = ? WHERE Id = ?",(0,1))
       
###### Salvataggio dei state per riavvio ##########################################################
def save_state():
    try:
        data_state = con.execute("SELECT * FROM data WHERE Id == 1")
        for row in data_state.fetchall():
            state.put("state", setTemp=row[3], Programma = row[7],Stato = row[8], ManualTemp = row[10], NoIce=row[2])
    except:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "Salva state",
            "FAILED to save data state " , timestamp=False)
###### Salvataggio dati grafico ###################################################################
def save_graph(dt):
    # save graph
    # conversione heatpin in temperatura 10=off 12=on
    global csvSaver
    Clock.unschedule(csvSaver)
    data_saver = con.execute("SELECT * FROM data WHERE Id == 1")
    for row in data_saver.fetchall():
        if row[7] == 0:
            switchTemp = 0
            graphTemperature = 0
            currentTemp = 0
        elif row[7] == 1:
            switchTemp = 0 if row[1] == 0  else 5
            if row[8] == 1:
                graphTemperature = row[3]
            elif row[8] == 2:
                graphTemperature = row[10]
            elif row[8] ==3:
                graphTemperature = row[2]
            elif row[8] == 0:
                graphTemperature = 0
            currentTemp = row[4]
        elif row[7] == 2:
            switchTemp = 0 if row[1] == 0 else -5
            if row[8] == 1:
                graphTemperature = row[3]
            elif row[8] == 2:
                graphTemperature = row[10]
            elif row[8] == 0:
                graphTemperature = 0
            currentTemp = row[4]

        # scrivo il file csv con i dati
    oggi = datetime.datetime.today().weekday()
    file_name = "./web/graph/" + "thermostat"+str(oggi)+".csv"
    if os.path.isfile(file_name):
        file_time = os.path.getmtime(file_name)
        test_time = datetime.datetime.fromtimestamp(file_time).strftime("%Y-%m-%d")
        if test_time <> datetime.datetime.now().strftime("%Y-%m-%d"):
                os.remove(file_name)
        ## file_name, datetime.datetime.fromtimestamp(file_time).strftime("%Y-%m-%d"),datetime.datetime.now().strftime("%Y-%m-%d")
    out_file = open(file_name, "a")
    out_file.write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ", " + str(graphTemperature) + ", " + str(
        currentTemp) + ", " + str(switchTemp) + "\n")
    out_file.close()
    csvSaver = Clock.schedule_once(save_graph, 300 if not (settings.exists("thermostat")) else settings.get("thermostat")["saveCsv"])
    
    
#### hei dht aggiornati !!!! ######################################################################

def aggiornaDht(dt):
    dht_aggiorna = con.execute("SELECT * FROM periferiche WHERE TipoDht == 2")
    for row in dht_aggiorna:
        t = Thread(target=dhtZoneSendThread(row[2]))
        t.start()


def dhtZoneSendThread(c):
    try:
        f = http.request('GET',c + "/aggiorna")
        log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/aggiorna: ",c,timestamp=False)
    except:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/aggiorna: ",c + " - ", timestamp=False)

    else:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/aggiorna: ",
           str(c)+ " - Disabled", timestamp=False)


###### il manager degli schermi ###################################################################

class Manager(ScreenManager):
    main_screen = ObjectProperty(None)
    min_screen = ObjectProperty(None)
    meteo_screen = ObjectProperty(None)
    boot_screeen = ObjectProperty(None)
    summer_screen = ObjectProperty(None)
    
###### la schermata per il riscaldamento ##########################################################

class MainScreen(Screen):
    main_time = ObjectProperty()
    main_date = ObjectProperty()
    main_umidita = StringProperty()
    main_setTemp = StringProperty()
    main_temp = ObjectProperty()
    main_auto = ObjectProperty()
    main_manual = ObjectProperty()
    main_meteo = StringProperty()
    main_meteo_text = StringProperty()
    main_caldaia = StringProperty()
    slider_color = NumericProperty()
    main_explain = StringProperty()
    main_set_setTemp = StringProperty()
    main_state = NumericProperty()
    main_next = StringProperty()
    main_off = NumericProperty()
    main_meteo_time = NumericProperty()
    start_off = 0
    
    def on_pre_enter(self):
        Clock.schedule_once(self.crono,0)
        Clock.schedule_once(self.meteo,.1)
        
    def on_enter(self):
        Clock.schedule_interval(self.crono,3)
        Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
        Clock.schedule_once(self.meteo,50)
        save_state()

        
    def on_leave(self):
        Clock.unschedule(self.crono)
        Clock.unschedule(self.meteo)
        Clock.unschedule(self.minimize_screen)
        
    def crono(self,*args):
        with thermostatLock:
            self.main_time.text = time.strftime("%H : %M").lower()
            self.main_date.text = time.strftime("%d - %B - %Y").lower()
            self.main_explain = ""
            data_main = con.execute("select * from data where Id == 1")
            for row in data_main.fetchall():                
                if (row[5] <> None):
                    self.main_umidita = str(int(row[5]))+" % - "+str(int(row[6]))+" mBar"
                else:
                    self.main_umidita =""
                self.main_temp.text = str(round(row[4],1))+"°"
                self.slider_color = row[1]
                if (row[8] == 1):
                    self.main_auto.state = 'down'
                    self.main_manual.state = 'normal'
                    self.main_setTemp = str(round(row[3],1))
                    self.main_next = "{:0>2d}".format(schedule.next_run().hour)+":"+"{:0>2d}".format(schedule.next_run().minute)+" --> "+str(min(schedule.jobs))[str(min(schedule.jobs)).find("(")+1:str(min(schedule.jobs)).find(")")]
                    self.main_state = 1
                elif (row[8] == 2):
                    self.main_manual.state = 'down'
                    self.main_auto.state = 'normal'
                    self.main_setTemp = str(round(row[10],1))
                    self.main_next = ""
                    self.main_state = 1
                elif (row[8] == 3):
                    self.main_manual.state = 'normal'
                    self.main_auto.state = 'normal' 
                    self.main_setTemp = "[size=24]NoIce \n[/size]"+str(round(row[2],1))
                    self.main_next = ""
                    self.main_state = 2
                else :
                    self.main_manual.state = 'normal'
                    self.main_auto.state = 'normal'
                    self.main_setTemp = "OFF"
                    self.main_next = ""
                    self.main_state = 10
                if (row[7] == 0 ):
                    self.main_programma = "OFF"
                elif (row[7] == 1 ):
                    self.main_programma = "Inverno"
            self.dhtview.disegna_schermo()
            # row                                                   
            ## timeb,self
            
    def meteo(self,*args):
        try: 
            setMeteoInterval = 300 if not (settings.exists("thermostat")) else settings.get("weather")["weatherRefreshInterval"]
            data_main = con.execute("select * from data where Id == 1")
            for row in data_main.fetchall():
                if time.time() -row[13] >= setMeteoInterval:
                    weatherLocation = settings.get("weather")["location"]
                    weatherAppKey = settings.get("weather")["appkey"]
                    weatherURLBase = "https://api.darksky.net/forecast/"
                    weatherURLTimeout = settings.get("weather")["URLtimeout"]
                    weatherURLCurrent = weatherURLBase + weatherAppKey + "/" + weatherLocation + "?units=si&exclude=[minutely,hourly,flags,alerts]&lang=it"
                    weatherExceptionInterval = settings.get("weather")["weatherExceptionInterval"] * 60
                    weatherRefreshInterval = settings.get("weather")["weatherRefreshInterval"] * 60
                    r = http.request('GET', weatherURLCurrent, timeout = 3)
                    weather = json.loads(r.data.decode('utf-8'))
                    # weather
                    outt = 0
                    press = 0
                    umi = 0
                    out_main = con.execute("select * from periferiche where TipoDht == 0")
                    for row in out_main:
                        if (row[3] > 0):
                            outt = round(row[3],1)
                        if (row[4] > 0):
                            umi = int(row[4])
                        if (row[5] > 0):
                            press = int(row[5])
                    if (outt == 0):
                        outt = round(weather["currently"]["temperature"],1)
                    if (umi == 0):
                        umi = int(weather["currently"]["humidity"] *100)
                    if (press == 0):
                        press = int(weather["currently"]["pressure"])
                    self.main_meteo = "web/images/" + weather["currently"]["icon"] + ".png"
                    self.main_meteo_text =  "[b]" + weather["currently"]["summary"] + "[/b]\nT out:[b] "+str(outt)+"[/b] c\nUmidita: [b]"+str(umi)+" %[/b]\nPressione:[b] "+str(press)+"mBar[/b]"
                    with thermostatLock:
                        con.execute("Update data SET Tout = ? , Pressione = ?, Umidita = ?, Meteo = ? WHERE Id = ?",(outt,press,umi,time.time(),1))
        except:
            self.main_meteo = "web/images/na.png"
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, "Update FAILED!")
            
    def update_schema(self, dato):
        with thermostatLock:
            #self.main_explain = "Sistema in Aggiornamento......"
            if dato <= 3 :
                con.execute("Update data  SET StatoSistema = ?, ProgSistema = ?  WHERE Id = ?" ,(dato,1,1))
                reloadSchedule()
                Clock.schedule_once(self.crono,0)
                change_system_settings()
                aggiornaDht(0.1)
                Clock.schedule_once(save_graph, .1)
                save_state()
     
    def update_temp(self,dato):
        with thermostatLock:
            registra = round(float(dato),1)
            #self.main_explain = "Sistema in Aggiornamento......"
            if self.main_manual.state == "down":
                con.execute("Update data SET ManTemp = ? WHERE Id = ?" ,(registra,1))
            elif self.main_auto.state == "down":
                con.execute("Update data SET SetTemp = ? , ManTemp = ? WHERE Id = ?" ,(registra,registra,1))
            Clock.schedule_once(self.crono,0)
            change_system_settings()
            aggiornaDht(0.1) 
            Clock.schedule_once(save_graph, .1)
            Clock.schedule_interval(self.crono,3)
            Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
            save_state()

            
    def minimize_screen(self ,*args):
        with thermostatLock:
            self.parent.current = 'minimize'
        
    def anti_minimize(self, *args):
        with thermostatLock:
            Clock.unschedule(self.minimize_screen)
            Clock.unschedule(self.crono)
            self.main_set_setTemp = self.main_setTemp
            
    def popup(self,dato):
        test1 = self.main_set_setTemp
        test2 = 15.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["minTemp"]
        test3 = 30.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["maxTemp"]
        #print(repr(test1))
        test = round(float(test1),1)
        test_finale = test + dato
        if test_finale <= test2:
            self.main_set_setTemp = str(test2)
        elif test_finale >= test3:
            self.main_set_setTemp = str(test3)
        else:
            self.main_set_setTemp = str(test_finale)
            
    def press_off_time(self, *args):
        if self.start_off <=3:
            self.main_explain = "Setto NOICE ......"
        elif self.start_off >=3 and self.start_off <=7:
            self.main_explain = "Spengo il Sistema ......"
        elif self.start_off >=8 :
            self.main_explain = "Chiudo Thermostat Ritorno al Sistema Operativo ......"
        self.start_off +=1
        
    def press_off(self,dato):
        with thermostatLock:
            if dato == 1:
                Clock.unschedule(self.crono)
                Clock.unschedule(self.minimize_screen)
                Clock.schedule_once(self.press_off_time,0)
                Clock.schedule_interval(self.press_off_time,1)
            elif dato == 2:
                Clock.unschedule(self.press_off_time)
                print self.start_off
                if self.start_off >= 8:
                    log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/exit", "Thermostat exit on call...", single=True)
                    
                    if logFile is not None:
                        logFile.flush()
                        os.fsync(logFile.fileno())
                        logFile.close()
                    
                    exit()  # This does not return!!!
                    
                    
                elif self.start_off >= 3 and self.start_off <= 7:
                    self.main_explain = "Spengo il sistema ......"
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ? WHERE Id = ?",(0,0,1))
                    change_system_settings()
                    aggiornaDht(0.1)
                    Clock.schedule_once(save_graph, .1)
                    Clock.schedule_interval(self.crono,3)
                    Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
                    save_state()
                    
                else  :
                    self.main_explain = "Setto Noice......"
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ? WHERE Id = ?",(3,1,1))
                    change_system_settings()
                    aggiornaDht(0.1)
                    Clock.schedule_once(save_graph, .1)
                    Clock.schedule_interval(self.crono,3)
                    Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
                    save_state()
                Clock.schedule_once(self.crono,0)
                Clock.schedule_once(save_graph, .1)
                Clock.schedule_interval(self.crono,3)
                Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
                self.start_off = 0
                
    def press_estate(self):
        with thermostatLock:
            con.execute("Update data SET ProgSistema = ?  WHERE Id = ?" ,(2,1))
            reloadSchedule()
            aggiornaDht(0.1)
            change_system_settings()
            self.parent.current = 'summer'
    
        
###### la schermata per l'estate ##########################################################

class SummerScreen(Screen):
    summer_time = ObjectProperty()
    summer_date = ObjectProperty()
    summer_umidita = StringProperty()
    summer_setTemp = StringProperty()
    summer_temp = ObjectProperty()
    summer_auto = ObjectProperty()
    summer_manual = ObjectProperty()
    summer_meteo = StringProperty()
    summer_meteo_text = StringProperty()
    summer_caldaia = StringProperty()
    summer_slider_color = NumericProperty()
    summer_explain = StringProperty()
    summer_set_setTemp = StringProperty()
    summer_state = NumericProperty()
    summer_next = StringProperty()
    summer_off = NumericProperty()
    start_off = 0
    
    def on_pre_enter(self):
        Clock.schedule_once(self.crono,0)
        Clock.schedule_once(self.meteo,.1)
        
    def on_enter(self):
        Clock.schedule_interval(self.crono,3)
        Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
        Clock.schedule_once(self.meteo,50)
        save_state()
    
    def on_leave(self):
        Clock.unschedule(self.crono)
        Clock.unschedule(self.meteo)
        Clock.unschedule(self.minimize_screen)
        
    def crono(self,*args):
        with thermostatLock:
            self.summer_time.text = time.strftime("%H : %M").lower()
            self.summer_date.text = time.strftime("%d - %B - %Y").lower()
            self.summer_explain = ""
            data_summer = con.execute("select * from data where Id == 1")
            for row in data_summer.fetchall():                
                if (row[5] <> None):
                    self.summer_umidita = str(int(row[5]))+" % - "+str(int(row[6]))+" mBar"
                else:
                    self.summer_umidita =""
                self.summer_temp.text = str(row[4])+"°"
                self.summer_slider_color = row[1]
                if (row[8] == 1):
                    self.summer_auto.state = 'down'
                    self.summer_manual.state = 'normal'
                    self.summer_setTemp = str(round(row[3],0))
                    self.summer_next = "{:0>2d}".format(schedule.next_run().hour)+":"+"{:0>2d}".format(schedule.next_run().minute)+" --> "+str(min(schedule.jobs))[str(min(schedule.jobs)).find("(")+1:str(min(schedule.jobs)).find(")")]
                    self.summer_state = 1
                elif (row[8] == 2):
                    self.summer_manual.state = 'down'
                    self.summer_auto.state = 'normal'
                    self.summer_setTemp = str(round(row[10],0))
                    self.summer_next = ""
                    self.summer_state = 1
                else :
                    self.summer_manual.state = 'normal'
                    self.summer_auto.state = 'normal'
                    self.summer_setTemp = "OFF"
                    self.summer_next = ""
                    self.summer_state = 0
                if (row[7] == 0 ):
                    self.summer_programma = "OFF"
                elif (row[7] == 1 ):
                    self.summer_programma = "Inverno"
            dht_summer = con.execute("select * from periferiche WHERE TipoDht == 2")
            self.summer_explain_dht = ""
            for row in dht_summer:
                self.summer_explain_dht += row[1] +"[b] : "+str(row[3])+"c[/b]\n"
            self.dhtview.disegna_schermo()
            # row                                                   
        ## timeb,self
    def meteo(self,*args):
        try:
            weatherLocation = settings.get("weather")["location"]
            weatherAppKey = settings.get("weather")["appkey"]
            weatherURLBase = "https://api.darksky.net/forecast/"
            weatherURLTimeout = settings.get("weather")["URLtimeout"]
            weatherURLCurrent = weatherURLBase + weatherAppKey + "/" + weatherLocation + "?units=si&exclude=[minutely,hourly,flags,alerts]&lang=it"
            weatherExceptionInterval = settings.get("weather")["weatherExceptionInterval"] * 60
            weatherRefreshInterval = settings.get("weather")["weatherRefreshInterval"] * 60
            r = http.request('GET', weatherURLCurrent)
            weather = json.loads(r.data.decode('utf-8'))
            # weather
            outt = 0
            press = 0
            umi = 0
            out_summer = con.execute("select * from periferiche where TipoDht == 0 OR TipoDht = 6")
            for row in out_summer:
                if (row[3] > 0):
                    outt = round(row[3],1)
                if (row[4] > 0):
                    umi = int(row[4])
                if (row[5] > 0):
                    press = int(row[5])
            if (outt == 0):
                outt = round(weather["currently"]["temperature"],1)
            if (umi == 0):
                umi = int(weather["currently"]["humidity"] *100)
            if (press == 0):
                press = int(weather["currently"]["pressure"])
            self.summer_meteo = "web/images/" + weather["currently"]["icon"] + ".png"
            self.summer_meteo_text =  "[b]" + weather["currently"]["summary"] + "[/b]\nT out:[b] "+str(outt)+"[/b] c\nUmidita: [b]"+str(umi)+" %[/b]\nPressione:[b] "+str(press)+"mBar[/b]"
            with thermostatLock:
                con.execute("Update data SET Tout = ? , Pressione = ?, Umidita = ? WHERE Id = ?",(outt,press,umi,1))
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, "Update FAILED!")
            
    def update_schema(self, dato):
        with thermostatLock:
            #self.main_explain = "Sistema in Aggiornamento......"
            if dato <= 3 :
                con.execute("Update data  SET StatoSistema = ?, ProgSistema = ?  WHERE Id = ?" ,(dato,2,1))
                reloadSchedule()
                Clock.schedule_once(self.crono,0)
                change_system_settings()
                aggiornaDht(0.1)
                Clock.schedule_once(save_graph, .1)
                save_state()
            
    def update_temp(self,dato):
        with thermostatLock:
            registra = round(float(dato),1)
            #self.main_explain = "Sistema in Aggiornamento......"
            if self.summer_manual.state == "down":
                con.execute("Update data SET ManTemp = ? WHERE Id = ?" ,(registra,1))
            elif self.summer_auto.state == "down":
                con.execute("Update data SET SetTemp = ? , ManTemp = ? WHERE Id = ?" ,(registra,registra,1))
            Clock.schedule_once(self.crono,0)
            change_system_settings()
            aggiornaDht(0.1) 
            Clock.schedule_once(save_graph, .1)
            Clock.schedule_interval(self.crono,3)
            Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
            save_state()
            
    def minimize_screen(self ,*args):
        with thermostatLock:
            self.parent.current = 'minimize'
        
    def anti_minimize(self):
        with thermostatLock:
            Clock.unschedule(self.minimize_screen)
            Clock.unschedule(self.crono)
            self.summer_set_setTemp = self.summer_setTemp
            #Clock.schedule_interval(self.crono,3)
            
    def popup(self,dato):
        test1 = self.summer_set_setTemp
        test2 = 15.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["minTemp"]
        test3 = 30.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["maxTemp"]
        #print(repr(test1))
        test = round(float(test1),1)
        test_finale = test + dato
        if test_finale <= test2:
            self.summer_set_setTemp = str(test2)
        elif test_finale >= test3:
            self.summer_set_setTemp = str(test3)
        else:
            self.summer_set_setTemp = str(test_finale)  
            
    def press_off_time(self, *args):
        if self.start_off <=5:
            self.summer_explain = "Spengo il Sistema ......"
        elif self.start_off >=5 :
            self.summer_explain = "Chiudo Thermostat Ritorno al Sistema Operativo ......"
        self.start_off +=1
        
    def press_off(self,dato):
        with thermostatLock:
            if dato == 1:
                Clock.unschedule(self.crono)
                Clock.unschedule(self.minimize_screen)
                Clock.schedule_once(self.press_off_time,0)
                Clock.schedule_interval(self.press_off_time,1)
            elif dato == 2:
                Clock.unschedule(self.press_off_time)
                print self.start_off
                if self.start_off >= 5:
                    log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/exit", "Thermostat exit on call...", single=True)
                    
                    if logFile is not None:
                        logFile.flush()
                        os.fsync(logFile.fileno())
                        logFile.close()
                    
                    exit()  # This does not return!!!
                    
                else  :
                    self.main_explain = "Spengo Sistema......"
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ? WHERE Id = ?",(0,0,1))
                    change_system_settings()
                    aggiornaDht(0.1)
                    Clock.schedule_once(save_graph, .1)
                    Clock.schedule_interval(self.crono,3)
                    Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
                    save_state()
                Clock.schedule_once(self.crono,0)
                Clock.schedule_once(save_graph, .1)
                Clock.schedule_interval(self.crono,3)
                Clock.schedule_once(self.minimize_screen,20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"])
                self.start_off = 0
            
    def press_inverno(self):
        with thermostatLock:
            con.execute("Update data SET ProgSistema = ?  WHERE Id = ?" ,(1,1))
            reloadSchedule()
            aggiornaDht(0.1)
            change_system_settings()
            Clock.schedule_once(save_graph, .1)
            self.parent.current = 'main'
        
###### la schermata mini ##########################################################################

class MinScreen(Screen):
    min_data = StringProperty()
    label_data = ObjectProperty()
    def on_pre_enter(self):
        self.label_data.pos = (60,50)
        anim = Animation(pos=(630, 350), t='linear', d=100)
        anim += Animation(pos=(60, 350), t='linear', d=100)
        anim += Animation(pos=(630, 50), t='linear', d=100)
        anim += Animation(pos=(60, 50), t='linear', d=100)
        anim.repeat = True
        anim.start(self.label_data)
    def on_enter(self):
        Clock.schedule_interval(self.ticks.update_clock,1)
        Clock.schedule_once(self.crono,.1)
        Clock.schedule_interval(self.crono,5)
        Clock.schedule_once(self.spegni_schermo,60 if not (settings.exists("thermostat")) else settings.get("thermostat")["lightOff"])
    def on_leave(self):
        Clock.unschedule(self.ticks.update_clock)
    def crono(self,*args):
        tStato = ""
        tCaldaia = ""
        tProgramma = ""
        data_main = con.execute("select * from data where Id == 1")
        for row in data_main.fetchall():                
            if row[7] == 0:
                tProgramma = "Spento"
            elif row[7] == 1:
                tProgramma = "Inverno"
            elif row[7] == 2:
                tProgramma = "Estate"
            if row[8] == 3:
                tStato = "NoIce"
            elif row[8] == 1:
                tStato = "Auto"
            elif row[8] == 2:
                tStato = "Manuale"
            if row[1] == 0:
                tCaldaia = "OFF"
            elif row[1] ==1:
                tCaldaia ="ON"
            self.min_data = "[size=30]Temp :[b]  " + str(row[4])+"[/b][/size]\nset Temp:[b]       "+str(row[3])+"[/b]\nCaldaia:[b]           "+tCaldaia+"[/b]\nProgramma:[b]  "+tProgramma+"[/b]\nSistema:[b]          "+tStato+"[/b]"
            
    def return_screen(self):
        data_min = con.execute("select * from data where Id == 1")
        for row in data_min.fetchall(): 
            if row[7] == 2:
                self.parent.current = 'summer'
            else:
                self.parent.current = 'main'
    
    def spegni_schermo(self, *args):
        GPIO.output(lightPin, GPIO.LOW)
        
##### la schermata delle previsioni meteo #########################################################

class MeteoScreen(Screen):
    label1 = StringProperty()
    label2 = StringProperty()
    label3 = StringProperty()
    image1 = StringProperty()
    image2 = StringProperty()
    image3 = StringProperty()
    day1 = StringProperty()
    day2 = StringProperty()
    day3 = StringProperty()
    
    def on_pre_enter(self):
        Clock.schedule_once(self.previsioni,0)
    def on_enter(self):
        Clock.schedule_once(self.main_return,15)
    
    def on_leave(self):
        Clock.unschedule(self.main_return)
    
    def main_return(self ,*args):
        data_meteo = con.execute("select * from data where Id == 1")
        for row in data_meteo.fetchall(): 
            if row[7] == 2:
                self.parent.current = 'summer'
            else:
                self.parent.current = 'main'
        
    def previsioni(self,*args):
        try:
            weatherLocation = settings.get("weather")["location"]
            weatherAppKey = settings.get("weather")["appkey"]
            weatherURLBase = "https://api.darksky.net/forecast/"
            weatherURLTimeout = settings.get("weather")["URLtimeout"]
            weatherURLCurrent = weatherURLBase + weatherAppKey + "/" + weatherLocation + "?units=si&exclude=[minutely,hourly,flags,alerts]&lang=it"
            weatherExceptionInterval = settings.get("weather")["weatherExceptionInterval"] * 60
            weatherRefreshInterval = settings.get("weather")["weatherRefreshInterval"] * 60
            r = http.request('GET', weatherURLCurrent)
            weather = json.loads(r.data.decode('utf-8'))
            # weather
            ###today = weather["daily"]["data"][c]
            self.day1 = "[b]" + time.strftime('%A  %d/%m ', time.localtime(weather["daily"]["data"][0]["time"])) + "[/b]"
            self.day2 = "[b]" + time.strftime('%A  %d/%m ', time.localtime(weather["daily"]["data"][1]["time"])) + "[/b]"
            self.day3 = "[b]" + time.strftime('%A  %d/%m ', time.localtime(weather["daily"]["data"][2]["time"])) + "[/b]"
            self.image1 = "web/images/" + weather["daily"]["data"][0]["icon"] + ".png"
            self.image2 = "web/images/" + weather["daily"]["data"][1]["icon"] + ".png"
            self.image3 = "web/images/" + weather["daily"]["data"][2]["icon"] + ".png"
            ##        forecastSummaryLabel = "[b]" + today["summary"][:-1] + "[/b] "
            self.label1= "\n".join(("[b]" + weather["daily"]["data"][0]["summary"][:-1] + "[/b]\n",
                    "[b]Max: [/b]" + str(int(round(weather["daily"]["data"][0]["temperatureMax"], 0))) + "[b]  Min: [/b]" + str(int(round(weather["daily"]["data"][0]["temperatureMin"], 0))),
                    "[b]Umidita: [/b]" + str(weather["daily"]["data"][0]["humidity"] * 100) + "%",
                    "[b]Nuvole: [/b]" + str(weather["daily"]["data"][0]["cloudCover"] * 100) + "%",
                    "[b]Pressione: [/b]" + str(int(weather["daily"]["data"][0]["pressure"])) + "mBar",
                    "[b]Vento: [/b]" + str(int(round(weather["daily"]["data"][0]["windSpeed"] * windFactor))) + windUnits + " " + self.get_cardinal_direction(                        weather["daily"]["data"][0]["windBearing"]),
                    "[b]Alba: [/b]"+ time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][0]["sunriseTime"])),
                    "[b]Tramonto: [/b]"+time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][0]["sunsetTime"])),
                    ))
            self.label2= "\n".join(("[b]" + weather["daily"]["data"][1]["summary"][:-1] + "[/b]\n",
                    "[b]Max: [/b]" + str(int(round(weather["daily"]["data"][1]["temperatureMax"], 0))) + " [b] Min: [/b]" + str(int(round(weather["daily"]["data"][1]["temperatureMin"], 0))),
                    "[b]Umidita: [/b]" + str(weather["daily"]["data"][1]["humidity"] * 100) + "%",
                    "[b]Nuvole: [/b]" + str(weather["daily"]["data"][1]["cloudCover"] * 100) + "%",
                    "[b]Pressione: [/b]" + str(int(weather["daily"]["data"][1]["pressure"])) + "mBar",
                    "[b]Vento: [/b]" + str(int(round(weather["daily"]["data"][1]["windSpeed"] * windFactor))) + windUnits + " " + self.get_cardinal_direction(                        weather["daily"]["data"][1]["windBearing"]),
                    "[b]Alba: [/b]"+ time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][1]["sunriseTime"])),
                    "[b]Tramonto: [/b]"+time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][1]["sunsetTime"])),
                    ))
            self.label3= "\n".join(("[b]" + weather["daily"]["data"][2]["summary"][:-1] + "[/b]\n",
                    "[b]Max: [/b]" + str(int(round(weather["daily"]["data"][2]["temperatureMax"], 0))) + "  [b]Min: [/b]" + str(int(round(weather["daily"]["data"][2]["temperatureMin"], 0))),
                    "[b]Umidita: [/b]" + str(weather["daily"]["data"][2]["humidity"] * 100) + "%",
                    "[b]Nuvole: [/b]" + str(weather["daily"]["data"][2]["cloudCover"] * 100) + "%",
                    "[b]Pressione: [/b]" + str(int(weather["daily"]["data"][2]["pressure"])) + "mBar",
                    "[b]Vento: [/b]" + str(int(round(weather["daily"]["data"][2]["windSpeed"] * windFactor))) + windUnits + " " + self.get_cardinal_direction(                        weather["daily"]["data"][2]["windBearing"]),
                    "[b]Alba: [/b]"+ time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][2]["sunriseTime"])),
                    "[b]Tramonto: [/b]"+time.strftime('%H:%M:%S ', time.localtime(weather["daily"]["data"][2]["sunsetTime"])),
                    ))
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, "Update FAILED!")
        
    def get_cardinal_direction(self,heading):
        directions = ["Nord", "NEst", "Est", "SEst", "Sud", "SOvest", "Ovest", "NOvest", "Nord"]
        return directions[int(round(((heading % 360) / 45)))]

###### Classe boot splash #########################################################################

class BootScreen(Screen):
    tempo = StringProperty()
    start_tempo = 5
    def on_enter(self):
        Clock.schedule_interval(self.countlabel,1)
    def on_leave(self):
        Clock.unschedule(self.countlabel)
        
    #def start(self,*args):
        #self.parent.current = 'main'   
    def countlabel(self,*args):
        self.start_tempo
        self.tempo = str(self.start_tempo)
        self.start_tempo -=1
        if self.start_tempo == 0 :
            data_execute = con.execute("SELECT * FROM data WHERE Id == 1")
            for row in data_execute.fetchall():
            # row
                if row[7] == 2:
                    self.parent.current = "summer"
                else:
                    self.parent.current = "main"
            
       


###### classe per disegnare orologio nella schermata mini #########################################

class Ticks(Widget):
    def __init__(self, **kwargs):
        super(Ticks, self).__init__(**kwargs)
        self.bind(pos=self.update_clock)
        self.bind(size=self.update_clock)
        
    def update_clock(self, *args):
        if pirEnabled:
            if GPIO.input(pirPin):
                log(LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, "1")
                GPIO.output(lightPin, GPIO.HIGH)
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
                Manager.current="main"
        self.canvas.clear()
        with self.canvas:
            time = datetime.datetime.now()
            Color(0.1, 0.8, 0.2,0.2)
            Line(points=[self.center_x, self.center_y, self.center_x+0.8*self.r*sin(pi/30*time.second), self.center_y+0.8*self.r*cos(pi/30*time.second)], width=1, cap="round")
            Color(0.3, 0.8, 0.3,0.2)
            Line(points=[self.center_x, self.center_y, self.center_x+0.7*self.r*sin(pi/30*time.minute), self.center_y+0.7*self.r*cos(pi/30*time.minute)], width=2, cap="round")
            Color(0.4, 0.7, 0.4,0.2)
            th = time.hour*60 + time.minute
            Line(points=[self.center_x, self.center_y, self.center_x+0.5*self.r*sin(pi/360*th), self.center_y+0.5*self.r*cos(pi/360*th)], width=3, cap="round")

###### dht page dynamically loaded ################################################################
class Dhtview(Widget):
    def __init__(self, **kwargs):
        super(Dhtview, self).__init__(**kwargs)
        self.bind(pos=self.disegna_schermo)
        self.bind(size=self.disegna_schermo)
        
    def disegna_schermo(self,*args):
        with thermostatLock:
            self.canvas.clear()
            dht_num = 0
            dhtLabel = {}
            dht_val = {}
            dht_type = {}
            dht_rect = {}
            dht_x = 10
            dht_y = 140
            dht_sposta_x = 130
            dht_sposta_y = 80
            dhtS_main = con.execute("select * from periferiche where TipoDht == 2 OR TipoDht = 3")
            for row in dhtS_main:
                #print row
                dht_num += 1
                dhtLabel[dht_num,0] = Label(text=row[1], size_hint=(None, None), font_size='14sp', markup=True, size=(120, 20),
                                 color=(1, 1, 1, 1),pos = (dht_x,dht_y),text_size = (120,20), halign="center")
                dhtLabel[dht_num,1] = Label(text="[b]"+str(row[3])+"°[/b] - "+str(row[4])+"%", size_hint=(None, None), font_size='18sp', markup=True, size=(120, 20),
                                 color=(1, 1, 1, 1),pos = (dht_x,(dht_y-25)),text_size = (120,20), halign="center")
                dhtLabel[dht_num,3] = Label(text="Set : [b]"+str(row[6])+"°[/b]", size_hint=(None, None), font_size='16sp', markup=True, size=(120, 20),
                                 color=(1, 1, 1, 1),pos = (dht_x,(dht_y-50)),text_size = (120,20), halign="center")
                dht_rect[dht_num,0] = dht_x -2
                dht_rect[dht_num,1] = dht_y +22
                dht_x = dht_x+dht_sposta_x
                if row[6] >= row[3] :
                    dht_val[dht_num,0] = 1 
                else:
                    dht_val[dht_num,0] = 0    
                if dht_num == 6 :
                    dht_x = 10
                    dht_y = dht_y -dht_sposta_y
                dht_type[dht_num] = row[7]
            for c in range(1,dht_num+1):
                #print c
                with self.canvas:
                    with dhtLabel[c,0].canvas.before:
                        Rectangle(pos=(dht_rect[c,0],dht_rect[c,1]), size=(124,-72),source='web/images/rect.png')
                        if dht_type[c] == 2:
                            Color(0.956, 0.498, 0.121,0.7)
                        else :
                            Color(0.027, 0.133, 0.713,0.7)
                        Rectangle(pos=dhtLabel[c,0].pos, size=dhtLabel[c,0].size)
                    with dhtLabel[c,3].canvas.before:
                        if dht_val[c,0]== 0:
                            Color(0.066, 0.917, 0.043, 1) 
                        else:
                            Color(0.839, 0, 0.152, 1)
                    Rectangle(pos=dhtLabel[c,3].pos, size=dhtLabel[c,3].size)
                self.add_widget(dhtLabel[c,0])
                self.add_widget(dhtLabel[c,1])
                self.add_widget(dhtLabel[c,3])

###### schedule implementation ####################################################################

def startScheduler():
    log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Started")
    while True:
        with scheduleLock:
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Running pending")
            schedule.run_pending()

        time.sleep(10)


def setScheduledTemp(temp):
    with thermostatLock:
            setTemp = round(temp, 1)
            con.execute("UPDATE data SET  SetTemp = ?,Switch = ?  WHERE Id = ?",(setTemp,1,1))
            salvaTempiTemp()
            log(LOG_LEVEL_STATE, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEMPERATURE, str(setTemp))


def getTestSchedule():
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    testSched = {}
    for i in range(len(days)):
        tempList = []
        for minute in range(60 * 24):
            hrs, mins = divmod(minute, 60)
            tempList.append([
                str(hrs).rjust(2, '0') + ":" + str(mins).rjust(2, '0'),
                float(i + 1) / 10.0 + ((19.0 if tempScale == "metric" else 68.0) if minute % 2 == 1 else (
                22.0 if tempScale == "metric" else 72.0))
            ])

        testSched[days[i]] = tempList

    return testSched

def reloadSchedule():
    with scheduleLock:
        schedule.clear()
        activeSched = None
        schedule_tipo = 0
        with thermostatLock:
            thermoSched = JsonStore("./setting/thermostat_schedule.json")
            schedule_main = con.execute("select * from data where Id == 1")
            for row in schedule_main.fetchall():
                schedule_tipo = row[7]
            if schedule_tipo  == 2:
                activeSched = thermoSched["cool"]
                log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "cool")
            elif schedule_tipo == 1:
                activeSched = thermoSched["heat"]
                log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "heat")
            if useTestSchedule:
                activeSched = getTestSchedule()
                log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "test")
            #  "Using Test Schedule!!!"

        if activeSched != None:
            for day, entries in activeSched.iteritems():
                for i, entry in enumerate(entries):
                    getattr(schedule.every(), day).at(entry[0]).do(setScheduledTemp, entry[1])
                    log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT,
                        "Set " + day + ", at: " + entry[0] + " = " + str(entry[1]) )


##############################################################################
#                                                                            #
#       Web Server Interface                                                 #
#                                                                            #
##############################################################################

##############################################################################
#      encoding: UTF-8                                                       #
# Form based authentication for CherryPy. Requires the                       #
# Session tool to be loaded.                                                 #
##############################################################################
cherrypy.server.socket_host = '0.0.0.0'

SESSION_KEY = '_cp_username'

def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    # Adapt to your needs
    if username in (settings.get( "thermostat" )[ "user" ]) and password == settings.get( "thermostat" )[ "pass" ]:
        return None
    else:
        return u"Username o Password errato."
    
    # An example implementation which uses an ORM could be:
    # u = User.get(username)
    # if u is None:
    #     return u"Username %s is unknown to me." % username
    # if u.password != md5.new(password).hexdigest():
    #     rebackground_normal: 'images/off.png'turn u"Incorrect password"

def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    if settings.get("web")["auth"] == 1:
        conditions = cherrypy.request.config.get('auth.require', None)
        if conditions is not None:
            username = cherrypy.session.get(SESSION_KEY)
            if username:
                cherrypy.request.login = username
                for condition in conditions:
                    # A condition is just a callable that returns true or false
                    if not condition():
                        raise cherrypy.HTTPRedirect("/auth/login")
            else:
                raise cherrypy.HTTPRedirect("/auth/login")
    else:
        return None
cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate


# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.

def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        return cherrypy.request.login == 'termo' and groupname == 'admin'
    return check

def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

# These might be handy

def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):
    
    def on_login(self, username):
        """Called on successful login"""
    
    def on_logout(self, username):
        """Called on logout"""
    
    def get_loginform(self, username, msg="Login ", from_page="/"):
	
        file = open( "web/html/thermostat_login.html", "r" )

        html = file.read()

        file.close()
		
        return html %locals()

    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.get_loginform("", from_page=from_page)
        
        error_msg = check_credentials(username, password)
        if error_msg:
            return self.get_loginform(username, error_msg, from_page)
        else:
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")
    
    @cherrypy.expose
    def logout(self, from_page="/"):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/")


class WebInterface(object):
        
    _cp_config = {
        'tools.sessions.on': True,
        'tools.auth.on': True
        }
    
    auth = AuthController()
    
    @cherrypy.expose
    @require()
        
    
    def index(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,"Served thermostat.html to: " + cherrypy.request.remote.ip)

        file = open("web/html/thermostat.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:
            wStato = ""
            wCaldaia = ""
            wProgramma = ""
            web_main = con.execute("select * from data where Id == 1")
            for row in web_main.fetchall():
                html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
                if row[8] == 1:
                    html = html.replace("@@temp@@", str(round(row[3],1)))
                elif row[8] == 2:
                    html = html.replace("@@temp@@", str(round(row[10],1)))
                elif row[8] == 3:
                    html = html.replace("@@temp@@", str(round(row[2],1)))
                html = html.replace("@@current@@", str(round(row[4],1)))
                mintemp = 15.0 if not settings.exists("thermostat") else settings.get("thermostat")["minTemp"]
                maxtemp = 30.0 if not settings.exists("thermostat") else settings.get("thermostat")["maxTemp"]
                html = html.replace("@@minTemp@@", str(mintemp))
                html = html.replace("@@maxTemp@@", str(maxtemp))
                html = html.replace("@@tempStep@@", str(0.1 if (row[7] == 1) else 1))
                html = html.replace("@@outtemp@@",str(row[9]))
                if row[7] == 0:
                    wProgramma = "Spento"
                elif row[7] == 1:
                    wProgramma = "Inverno"
                elif row[7] == 2:
                    wProgramma = "Estate"
                if row[8] == 3:
                    wStato = "NoIce"
                elif row[8] == 1:
                    wStato = "Auto"
                elif row[8] == 2:
                    wStato = "Manuale"
                elif row[8] == 0:
                    wStato = "Off"
                if row[1] == 0:
                    wCaldaia = "OFF"
                elif row[1] ==1:
                    wCaldaia ="ON"
            #html = html.replace("@@status@@", status)
            html = html.replace("@@programma@@", wProgramma)
            html = html.replace("@@stato@@", wStato)
            html = html.replace("@@caldaia@@", wCaldaia)
            
            #html = html.replace("@@dhtIrsubmit@@", "style='display:none'" if dhtIr_number == 0 else "")
            #html = html.replace("@@dhtZonesubmit@@", "style='display:none'" if dhtZone_number == 0 else "")
            #html = html.replace("@@dhtsubmit@@", "style='display:none'" if dhtEnabled == 0 else "")
            #if dhtZone_number == 0:
            #    html = html.replace("@@displayzone@@", "display:none")
            #if dhtIr_number == 0:
            #    html = html.replace("@@displayir@@", "display:none")
            #if dhtEnabled == 0:
            #    html = html.replace("@@displaydht@@", "display:none")

        return html
    
    @cherrypy.expose
    @require()
    def set(self, temp = 0, programma = 0, stato = 0):

        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Set thermostat received from: " + cherrypy.request.remote.ip)

        #print temp,programma,stato
        with thermostatLock:
            print programma
            if programma == "0":
                con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ?  WHERE Id = ? ",(stato,programma,1))
            elif programma == "1":
                if stato == "3":
                    #print ("NoICE")
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ?  WHERE Id = ? ",(stato,programma,1))
                elif stato == "2":
                    #print ("Manuale")
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ? , ManTemp = ? WHERE Id = ? ",(stato,programma,temp,1))
                elif stato == "1":
                    #print ("Auto")
                    con.execute("UPDATE data SET SetTemp = ?,StatoSistema =?, ProgSistema = ?  WHERE Id = ? ",(temp,stato,programma,1))
            elif programma == "2":
                if stato == "2":
                    con.execute("UPDATE data SET StatoSistema =?, ProgSistema = ? , ManTemp = ? WHERE Id = ? ",(stato,programma,temp,1))
                elif stato == "1":
                    con.execute("UPDATE data SET SetTemp = ?,StatoSistema =?, ProgSistema = ?  WHERE Id = ? ",(temp,stato,programma,1))
        
        file = open("web/html/thermostat_set.html", "r")

        html = file.read()

        file.close()
        
        with thermostatLock:
            wStato = ""
            wCaldaia = ""
            wProgramma = ""
            web_main = con.execute("select * from data where Id == 1")
            for row in web_main.fetchall():
                html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
                if row[8] == 1:
                    html = html.replace("@@temp@@", str(round(row[3],1)))
                elif row[8] == 2:
                    html = html.replace("@@temp@@", str(round(row[10],1)))
                elif row[8] == 3:
                    html = html.replace("@@temp@@", str(round(row[2],1)))
                    
                html = html.replace("@@dt@@",time.strftime("%H:%M").lower())
                if row[7] == 0:
                    wProgramma = "Spento"
                elif row[7] == 1:
                    wProgramma = "Inverno"
                elif row[7] == 2:
                    wProgramma = "Estate"
                if row[8] == 3:
                    wStato = "NoIce"
                elif row[8] == 1:
                    wStato = "Auto"
                elif row[8] == 2:
                    wStato = "Manuale"
                elif row[8] == 0:
                    wStato = "Off"
            #html = html.replace("@@status@@", status)
            html = html.replace("@@programma@@", wProgramma)
            html = html.replace("@@stato@@", wStato)
            reloadSchedule()
            change_system_settings()
            Clock.schedule_once(save_graph, .1)
            save_state()
        return html
    
    @cherrypy.expose
    @require()
    def schedule(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Served thermostat_schedule.html to: " + cherrypy.request.remote.ip)
        file = open("web/html/thermostat_schedule.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:
            web_main = con.execute("select * from data where Id == 1")
            for row in web_main.fetchall():
                html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
                html = html.replace("@@minTemp@@", str(round(15.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["minTemp"],1)))
                html = html.replace("@@maxTemp@@", str(round(30.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["maxTemp"],1)))
                html = html.replace("@@tempStep@@", str(0.1 if row[7] == 1 else 1))
            
            #html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
            #                                                                           "</b>") + ", " + timeLabel.text.replace(
            #    "[b]", "<b>").replace("[/b]", "</b>"))

        return html

    @cherrypy.expose
    @require()
    @cherrypy.tools.json_in()
    def save(self):
        log(LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Set schedule received from: " + cherrypy.request.remote.ip)
        schedule = cherrypy.request.json

        with scheduleLock:
            file = open("./setting/thermostat_schedule.json", "w")

            file.write(json.dumps(schedule, indent=4))

            file.close()

        reloadSchedule()
        change_system_settings()
        Clock.schedule_once(save_graph, .1)

        file = open("web/html/thermostat_saved.html", "r")

        html = file.read()

        file.close()

        #with thermostatLock:
           # html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
           # html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
           #                                                                            "</b>") + ", " + timeLabel.text.replace(
           #     "[b]", "<b>").replace("[/b]", "</b>"))

        return html

    @cherrypy.expose
    @require()
    def graph(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "graph.html to: " + cherrypy.request.remote.ip)
        file = open("web/html/graph.html", "r")

        html = file.read()
        file.close()

        return html

    #@cherrypy.expose
   # @cherrypy.tools.json_out()
    #def dht(self,nome,ip,templetta,umiditaletta,pressioneletta,tipodht, statodht):
    #    with thermostatLock:
   #         test = 0
    #        web_dht = con.execute("select * from data where Id == 1")
    #        for row in web_dht.fetchall():
     #           setta = row[3]
     #           stato = row[8]
     #           prog = row[7]
     #           manTemp = row[10]
      #          ice = row[2]
      #          caldaia = row[1]
      #      dht = [(nome,ip,templetta,umiditaletta,pressioneletta,0,tipodht,statodht)]
      #      dht_test = con.execute("select * from periferiche WHERE Nome == '"+nome+"'")
      #      for row in dht_test.fetchall():
      #          test = 1
      #      if (test > 0):
      #          con.execute("UPDATE periferiche SET Nome = ?,Ip = ?,TempLetta = ?, UmiditaLetta = ?,PressioneLetta = ?,Progressivo = ?,TipoDht = ?,StatoDht = ? WHERE Nome = ?",(nome,ip,templetta,umiditaletta,pressioneletta,0,tipodht,statodht,nome))
                # "update"
       #     else:
       #         con.executemany("INSERT INTO periferiche(Nome ,Ip ,TempLetta ,UmiditaLetta ,PressioneLetta ,Progressivo ,TipoDht ,StatoDht ) values (?,?,?,?,?,?,?,?)",dht)
                # "Salva"
        #    return {"setta": setta,"stato":stato,"programma":prog,"manTemp":manTemp,"noIce":ice,"caldaia":caldaia}
      


def startWebServer():
    host = "discover" if not (settings.exists("web")) else settings.get("web")["host"]
    # cherrypy.server.socket_host = host if host != "discover" else get_ip_address()	# use machine IP address if host = "discover"
    cherrypy.server.socket_port = 80 if not (settings.exists("web")) else settings.get("web")["port"]
    if cherrypy.server.socket_port == 443:
        cherrypy.server.ssl_module = "pyopenssl"
        cherrypy.server.ssl_certificate = settings.get("web")["cert"]
        cherrypy.server.ssl_private_key = settings.get("web")["key"]

    log(LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
        "Starting on " + cherrypy.server.socket_host + ":" + str(cherrypy.server.socket_port))

    conf = {
        '/': {
            'tools.staticdir.root': os.path.abspath(os.getcwd()),
            'tools.staticfile.root': os.path.abspath(os.getcwd())
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/css'
        },
        '/javascript': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/javascript'
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/images'
        },
        '/schedule.json': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': './setting/thermostat_schedule.json'
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': './web/images/favicon.ico'
        },
        '/graph': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/graph'
        }

    }

    cherrypy.config.update(
        {'log.screen': debug,
         'log.access_file': "",
         'log.error_file': "./log/cherrypy.log",
         'server.thread_pool': 10
         }
    )

    cherrypy.quickstart(WebInterface(), '/', conf)

class RequestHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        
        request_path = self.path
        
        #print("\n----- Request Start ----->\n")
        #print(request_path)
        if request_path[:2] == "/?":
            testo = request_path[2:]
            testo1 = testo.split("&")
            #print testo,testo1
            #for current_word in testo1:
            #    print(current_word)
        #print(self.headers)
        #print("<----- Request End -----\n")
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with thermostatLock:
            if testo1[9] =="DHT":
                test = 0
                web_dht = con.execute("select * from data where Id == 1")
                for row in web_dht.fetchall():
                    setta = row[3]
                    stato = row[8]
                    prog = row[7]
                    manTemp = row[10]
                    ice = row[2]
                    caldaia = row[1]
                    #nome,ip,templetta,umiditaletta,pressioneletta,tipodht, statodht
                dht = [(testo1[0],testo1[1],testo1[2],testo1[3],testo1[4],testo1[5],testo1[6],testo1[7],testo1[8],0)]
                #print dht
                dht_test = con.execute("select * from periferiche WHERE Id == '"+testo1[0]+"'")
                for row in dht_test.fetchall():
                    #print row,testo1[1]
                    test += 1
                #print test
                if (test > 0):
                    con.execute("UPDATE periferiche SET Id = ?,Nome = ?,Ip = ?,TempLetta = ?, SetTemp = ?, UmiditaLetta = ?,PressioneLetta = ?,TipoDht = ?,StatoDht = ? , Progressivo = ? WHERE Id = ?",(testo1[0],testo1[1],testo1[2],testo1[3],testo1[4],testo1[5],testo1[6],testo1[7],testo1[8],0, testo1[0]))
                    # "update"
                else:
                    con.executemany("INSERT INTO periferiche(Id,Nome ,Ip ,TempLetta ,SetTemp,UmiditaLetta ,PressioneLetta ,TipoDht ,StatoDht,Progressivo) values (?,?,?,?,?,?,?,?,?,?)",dht)
                    # "Salva"
                self.wfile.write ("{\"setta\":"+ str(setta)+",\"stato\":"+str(stato)+",\"programma\":"+str(prog)+",\"manTemp\":"+str(manTemp)+",\"noIce\":"+str(ice)+",\"caldaia\":"+str(caldaia)+"}")
    def log_message(self, format, *args):
        #print args
        return    
    
    do_DELETE = do_GET
##########################################################################
## Telegram Section
#########################################################################
def logTermostat(errore):
    out_file = open(("./log/" + "telegramlog.csv"), "a")
    out_file.write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ", " + errore + "\n")
    out_file.close()
    
def closeTelegram(chat_id,dt):
    global telegramTimeout,chatIdTest,testTimeout
    if testTimeout > 0:
        try:
            bot.sendMessage(chat_id, "Bot disabilitato.... Stand bye")
        except telepot.exception.TelegramError:
            logTermostat("Error during Closing..")
    testTimeout = 0
    chatIdTest = 0
    
if settings.get("telegram")["enabled"] == 1:
    try:
        telepot.api._pools = {'default': urllib3.PoolManager(num_pools=3, maxsize=10, retries=6, timeout=30),}
        bot = telepot.Bot(settings.get("telegram")["token"])
		
    except:
	logTermostat("Timeout su Telegram")
    with thermostatLock:
        def handle(msg):
            global telegramTimeout, chatIdTest,testTimeout
            try:
                chat_id = msg['chat']['id']
                command = msg['text']
                #print 'Got command: %s' % command
                #print chat_id
                if command == "/"+ settings.get("telegram")["pwd"] and chatIdTest == 0:
                    chatIdTest = chat_id
                    testTimeout = 100
                    Clock.schedule_once(partial(closeTelegram,chat_id), telegramTimeout)
                    bot.sendMessage(chat_id, "Pwd OK - Bot Abilitato per id : "+ str(chatIdTest)+" per : "+str(telegramTimeout)+"sec")
                else:
                    if chatIdTest == chat_id and testTimeout > 0:
                        telegramCommand(command,chat_id)
            except telepot.exception.TelegramError:
                logTermostat("Error during Pwd access..")
def telegramCommand(command,chat_id):
    try:
        if command == "/ip":
            f = get("https://api.ipify.org").text
            look_ip = str(f)
            if cherrypy.server.socket_port == 443:
                bot.sendMessage(chat_id, "Da Internet Thermostat su: https://" + look_ip )
            else:
                bot.sendMessage(chat_id, "Da Internet Thermostat su: http://" + look_ip )
            ip_int = str(get_ip_address())
            if cherrypy.server.socket_port == 443:
                bot.sendMessage(chat_id, "Da Lan Thermostat su: https://" + ip_int )
            else:
                bot.sendMessage(chat_id, "Da Lan Thermostat su: http://" + ip_int )
        elif command == "/stato":
            bot.sendMessage(chat_id, test_ip())
        elif command == "/time":
            bot.sendMessage(chat_id, str(datetime.datetime.now().strftime("%H:%M -- %d/%m/%Y")))
        elif command[:8] == "/settemp":
            tempe_set = float(command[command.index(":")+1:])
            data_telegram= con.execute("SELECT * FROM data WHERE Id == 1")
            for row in data_telegram.fetchall():
                if row[8] == 2:
                    con.execute("Update data SET ManTemp = ? WHERE Id = ?" ,(temp_set,1))
                    bot.sendMessage(chat_id, "Man Temp : "+str(tempe_set))
                elif row[8] == 1:
                    con.execute("Update data SET SetTemp = ? WHERE Id = ?" ,(temp_set,1))
                    bot.sendMessage(chat_id, "Set Temp : "+str(tempe_set))
                else:
                    bot.sendMessage(chat_id, "Set Temp Non Possibile - NoIce Configurato")
            bot.sendMessage(chat_id, test_ip())
            save_state()
        elif command == "/help":
            risposta = "/ip : leggi ip Thermostat \n/time : leggi ora Thermostat \n/stato : leggi lo stato di Thermostat \n/settemp:20.0 : setta Temperatura \n/inverno : setta Sistema per inverno \n/estate : setta Sistema per Estate \n/manuale : Funzionamento Manuale \n/auto : Funzionamento Auto\n/noice: Funzionamento NoIce \n/off : Spegne il sistema \n/close : Chiude Bot in questa Connessione\n/help : leggi i comandi possibili"
            bot.sendMessage(chat_id,risposta)
        elif command == "/inverno":
            con.execute("Update data SET ProgSistema = ? ,StatoSistema = ? WHERE Id = ?" ,(1,1,1))
            bot.sendMessage(chat_id,"Settato Inverno Auto")
            bot.sendMessage(chat_id, test_ip())
            save_state()
        elif command == "/estate":
            con.execute("Update data SET ProgSistema = ? ,StatoSistema = ? WHERE Id = ?" ,(2,1,1))
            bot.sendMessage(chat_id,"Settato Estate Auto")
            bot.sendMessage(chat_id, test_ip())
            save_state()
        elif command == "/manuale":
            con.execute("Update data SET StatoSistema = ? WHERE Id = ?" ,(2,1))
            bot.sendMessage(chat_id,"Settato Manuale")
            bot.sendMessage(chat_id, test_ip())
            save_state()
        elif command == "/noice":
            con.execute("Update data SET ProgSistema = ?, StatoSistema = ? WHERE Id = ?" ,(1,3,1))
            bot.sendMessage(chat_id,"Settato Inverno NoIce")
            save_state()
        elif command =="/off":
            con.execute("Update data SET ProgSistema = ? WHERE Id = ?" ,(0,1))
            bot.sendMessage(chat_id,"Sistema Spento")
            bot.sendMessage(chat_id, test_ip())
            save_state()
        elif command == "/close":
            Clock.unschedule(closeTelegram)
            Clock.schedule_once(partial(closeTelegram,chat_id), 0.4)
            bot.sendMessage(chat_id, "Disabilitazione Bot......")
    except :
        logTermostat("Error during Command: "+command)

def test_ip():
    testo =""
    data_telegram= con.execute("SELECT * FROM data WHERE Id == 1")
    for row in data_telegram.fetchall():
            if row[7] == 1:
                testo = "Sistema Selezionato : Inverno " 
            elif row[7]==2:
                testo = "Sistema Selezionato : Estate" 
            else :
                testo = "Sistema Off"
            if row[8] == 1:
                testo += "\nProgramma: Auto\nSetTemp : " + str(row[3]) + "\nTemp IN : " + str(row[4]) 
            elif row[8] == 2:
                testo += "\nProgramma: Manuale\nSetTemp : " + str(row[10]) + "\nTemp IN : " + str(row[4]) 
            elif row[8] == 3:
                testo += "\nProgramma: NoIce\nSetTemp : " + str(row[2]) + "\nTemp IN : " + str(row[4])
            else:
                testo += "Sistema Spento \nTemp IN : " + str(row[4]) 
            
            
            testo += "\nSistema : "+("ON" if row[1]==1  else "OFF")
    return testo
###### classe app #################################################################################

class thermostatApp(App):
    def build(self):
        Clock.schedule_interval(change,10)
        Clock.schedule_once(check_sensor_temp,.1)
        Clock.schedule_interval(check_sensor_temp,4)
        csvSaver = Clock.schedule_once(save_graph, 300 if not (settings.exists("thermostat")) else settings.get("thermostat")["saveCsv"])
        m = Manager(transition=SwapTransition())
        return m
    
###### class main --- the startup --- #############################################################
def main():
    # Start Web Server
    webThread = threading.Thread(target=startWebServer)
    webThread.daemon = True
    webThread.start()
    # "web server"
    # Start Scheduler
    reloadSchedule()
    schedThread = threading.Thread(target=startScheduler)
    schedThread.daemon = True
    schedThread.start()
    ####Start http for dht ################
    server = HTTPServer(('', 9090), RequestHandler)
    dhtThread = threading.Thread(target = server.serve_forever)
    dhtThread.daemon = True
    dhtThread.start()
    ####Start thread Telegram
    if settings.get("telegram")["enabled"] == 1: 
        try:
            MessageLoop(bot, handle).run_as_thread()
        except telepot.exception.TelegramError:
           logTermostat("Telegram error on start.....")
    # Start Thermostat UI/App
    thermostatApp().run()    
###### the startup ################################################################################

if __name__ == '__main__':
    try:
       main()
    finally:
        log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/shutdown", "Thermostat Shutting Down...")
        GPIO.cleanup()
        if logFile is not None:
            logFile.flush()
            os.fsync(logFile.fileno())
            logFile.close()