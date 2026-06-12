import serial
from time import sleep
import threading

from lib.Misc import print_hex


class FingerPrintDevHelper:
    def __init__(self, devName, baudrate):
        self.recvData = []
        self.devName = devName
        self.baudrate = baudrate
        self.serial = serial.Serial(devName, baudrate, timeout=0.5)  # /dev/ttyUSB0
        if self.serial.isOpen():
            print("open success")
        else:
            print("open failed")
        self.t = threading.Thread(target=self.recv)
        self.t.start()

    def recv(self):
        """
        接收返回信息
        """
        while True:
            data = self.serial.read_all()
            if data != b'':
               # print("receive:")
                #print_hex(data)
                self.recvData += data
                while True:
                    lenth = len(self.recvData)
                    startPoint = 0
                    if lenth < 2:
                        break
                    for i in range(lenth - 1):
                        if self.recvData[i] == 0xEF and self.recvData[i+1] == 0x01:
                            startPoint = i
                            self.recvData = self.recvData[startPoint:]
                            break
                    headLen = lenth - startPoint
                    frameLen = 0
                    if headLen >= 9:
                        dataLen = self.recvData[7] * 256
                        dataLen += self.recvData[8]
                        frameLen = 9 + dataLen

                    if frameLen != 0:
                        realDataLen = len(self.recvData)
                        if realDataLen >= frameLen:
                            result = self.recvData[:frameLen]
                            self.SerialRecvCallbackFunc(result)
                            #print("result:")
                            #print_hex(result)
                            self.recvData = self.recvData[frameLen:]
                        else:
                            break
                        # print(frameLen)
                    else:
                        break
                # print("done:")
            sleep(0.02)

    def write(self, data):
        """
        指令串口写入
        """
        #print("send:")
        #print_hex(data)
        return self.serial.write(data)

    def wait(self):
        self.t.join

    def setListener(self, func):
        """
        串口监听回调函数
        """
        self.SerialRecvCallbackFunc = func

