from time import sleep

from lib.FingerPrintDevHelper import FingerPrintDevHelper
from lib.FingerPrintEncode import *
from lib.FingerPrintDecode import *


class FingerPrintDevManager:
    def __init__(self, devName, baudrate, devAddr=0xFFFFFFFF):
        self.resCode = False        #接收帧，返回值，true为成功false为失败
        self.devAddr = devAddr      #指纹设备地址
        self.searchRstCode = None   #识别指纹的结果码，参考枚举SearchCharRst，0为成功，1为错误，9为未找到
        self.foundTempleteId = None #识别指纹的模版ID
        self.foundScore = 0         #识别指纹的置信度
        self.isMarched = False      #指纹是否找到
        self.templetePage1 = []     #模版存储列表的第一个存储页
        self.templetePage2 = []     #模版存储列表的第二个存储页
        self.templetePage = 0       #当前请求的模版存储页码
        self.templeteCount = 0      #模版列表的总条数
        self.fingerPrintEncode = FingerPrintEncode()    #获得当前请求的命令码
        self.isTerminal = False     #阻塞请求中断标记，true时将直接结束阻塞函数请求
        self.isDone = False         #模块请求指令执行是否完成标记
        self.fingerPrintDevHelper = FingerPrintDevHelper(devName, baudrate) #指纹设备串口句柄
        self.fingerPrintDevHelper.setListener(self.dataRecv)    #指纹设备串口数据接收回调

    def waitAll(self):
        """
        指纹设备数据获取线程阻塞函数
        """
        self.fingerPrintDevHelper.wait()

    def dataRecv(self, data):
        """
        指纹设备数据处理回调函数
        Parameters:
          data - 接收到的数据
        """
        cmdCode = self.fingerPrintEncode.cmdCode
        if cmdCode == CMDCode.checkPwdCmd or cmdCode == CMDCode.getImageCmd or cmdCode == CMDCode.genCharCmd or \
                cmdCode == CMDCode.regMBCmd or cmdCode == CMDCode.storMBCmd:
            if isFingerFinded(data):
                self.isDone = True
            else:
                self.isDone = False

        if cmdCode == CMDCode.genCharCmd or cmdCode == CMDCode.regMBCmd:
            self.isDone = True

        if cmdCode == CMDCode.storMBCmd:
            self.isDone = True
            if isFingerFinded(data):
                self.isSuccess = True
            else:
                self.isSuccess = False

        if cmdCode == CMDCode.readTempleteNumCmd:
            self.templeteCount = getTempleteNum(data)
            self.isDone = True

        if cmdCode == CMDCode.readIndexTableCmd:
            if self.templetePage == 0:
                self.templetePage1 = getTempleteArray(data, self.templetePage)
            if self.templetePage == 1:
                self.templetePage2 = getTempleteArray(data, self.templetePage)
            self.isDone = True
        if cmdCode == CMDCode.searchMBCmd:
            try:
                rstArray = searchMB(data)
                self.searchRstCode = rstArray[0]
                if self.searchRstCode == SearchCharRst.found.value:
                    self.foundTempleteId = rstArray[1]
                    self.foundScore = rstArray[2]
                self.isDone = True
            except:
                pass

        if cmdCode == CMDCode.delCharCmd or \
                cmdCode == CMDCode.clrCharsCmd:
            if data[9] == 0:
                self.resCode = True
            else:
                self.resCode = False
            self.isDone = True

    def wait4Success(self, checkInterval):
        """
        阻塞函数，等待指令执行成功，即isDone为true
        Parameters:
          checkInterval - 轮询间隔
        """
        self.isDone = False
        while True:
            if self.isDone or self.isTerminal:
                break
            sleep(checkInterval)

    def wait4Failed(self, checkInterval):
        """
        阻塞函数，等待指令执行失败，即isDone为false
        Parameters:
          checkInterval - 轮询间隔
        """
        self.isDone = True
        while True:
            if not self.isDone or self.isTerminal:
                break
            sleep(checkInterval)

    def reExecUntilSuccess(self, cmd, checkInterval):
        """
        阻塞函数，重复发送请求指令，并等待该指令执行成功，即isDone为true
        Parameters:
          cmd - 请求指令帧
          checkInterval - 轮询间隔
        """
        self.isDone = False
        while True:
            if self.isDone or self.isTerminal:
                break
            self.fingerPrintDevHelper.write(cmd)
            sleep(checkInterval)

    def reExecUntilFailed(self, cmd, checkInterval):
        """
        阻塞函数，重复发送请求指令，并等待该指令执行失败，即isDone为false
        Parameters:
          cmd - 请求指令帧
          checkInterval - 轮询间隔
        """
        self.isDone = True
        while True:
            if not self.isDone or self.isTerminal:
                break
            self.fingerPrintDevHelper.write(cmd)
            sleep(checkInterval)

    def deviceInit(self, pwd=0x0000):
        """
        指纹设备初始化函数
        Parameters:
          pwd - 默认密码全0
        """
        self.isTerminal = False
        cmd = self.fingerPrintEncode.checkPwdFrame(self.devAddr, pwd)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)

    def recordeFingerPoint(self, fingerId, times, waitFingerUp, recognisePerTime):
        """
        指纹录制函数
        Parameters:
          fingerId - 录制指纹存储的模版ID
          times - 录制次数
          waitFingerUp - 第n次指纹抬起后回调
          recognisePerTime - 第n次指纹录制完成
        return: 布尔类型，True录制成功，False失败
        """
        self.isTerminal = False
        if times > 4:
            times = 4
        for i in range(times):
            print("请按下手指")
            cmd = self.fingerPrintEncode.getImageFrame(self.devAddr)
            self.reExecUntilSuccess(cmd, 1)
            if self.isTerminal:
                return
            cmd = self.fingerPrintEncode.genCharFrame(self.devAddr, i + 1)
            self.fingerPrintDevHelper.write(cmd)
            self.wait4Success(0.1)
            waitFingerUp(i + 1)
            cmd = self.fingerPrintEncode.getImageFrame(self.devAddr)
            self.reExecUntilFailed(cmd, 1)
            recognisePerTime(i + 1)
            if self.isTerminal:
                return
        cmd = self.fingerPrintEncode.regMBFrame(self.devAddr)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)
        cmd = self.fingerPrintEncode.storMBFrame(self.devAddr, 1, fingerId)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)
        if self.isSuccess:
            return True
        else:
            return False


    def discard(self):
        """
        结束阻塞的请求
        """
        self.isTerminal = True

    def readFingerTables(self):
        """
        指纹特征值列表获取
        """
        self.isTerminal = False
        self.templetePage1 = []
        self.templetePage2 = []
        self.templetePage = 0
        cmd = self.fingerPrintEncode.readIndexTableFrame(self.devAddr, self.templetePage)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)
        self.templetePage = 1
        cmd = self.fingerPrintEncode.readIndexTableFrame(self.devAddr, self.templetePage)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)

        return self.templetePage1 + self.templetePage2

    def checkFingerChar(self, startCharIdx, endCharIdx):
        """
        指纹识别
        Parameters:
          startCharIdx - 指纹特征值匹配起始ID
          endCharIdx - 指纹特征值匹配结束ID
        """
        self.isTerminal = False
        self.searchRstCode = None
        if endCharIdx < startCharIdx:
            return

        cmd = self.fingerPrintEncode.getImageFrame(self.devAddr)
        self.reExecUntilSuccess(cmd, 1)
        if self.isTerminal:
            return
        cmd = self.fingerPrintEncode.genCharFrame(self.devAddr, 1)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)
        cmd = self.fingerPrintEncode.searchMBFrame(self.devAddr, 1, startCharIdx, endCharIdx)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)
        foundId = None
        score = None

        if self.searchRstCode == SearchCharRst.found.value:
            foundId = self.foundTempleteId
            score = self.foundScore

        return [foundId, score]

    def delFingerChar(self, fingerId):
        """
        删除指纹特征
        Parameters:
          templeteId - 模版ID
        """
        self.resCode = False
        cmd = self.fingerPrintEncode.delCharFrame(self.devAddr, fingerId, 1)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)

        return self.resCode

    def clrFingerChar(self):
        """
        清空指纹特征
        """
        self.resCode = False
        cmd = self.fingerPrintEncode.clrCharsFrame(self.devAddr)
        self.fingerPrintDevHelper.write(cmd)
        self.wait4Success(0.1)

        return self.resCode
