from enum import Enum

from lib.Misc import *


class CMDCode(Enum):
    delCharCmd = 1 #删除模板
    clrCharsCmd = 2 #清空指纹库
    readTempleteNumCmd = 3 #读有效模板个数PS_ValidTempleteNum
    readIndexTableCmd = 4 #读索引表PS_ReadIndexTable
    checkPwdCmd = 5 #验证口令PS_VfyPwd
    getImageCmd = 6 #获取图像PS_GetImage
    genCharCmd = 7 #生成特征 PS_GenChar
    regMBCmd = 8 #合并模板 PS_RegMB
    storMBCmd = 9 #存储模板 PS_StorMB
    searchMBCmd = 10 #搜索模板 PS_SearchMB
    uploadImgCmd = 11 #上传图像 PS_UpImage
    readDevInfoCmd = 12 #读取系统基本参数 PS_ReadSysPara


class FingerPrintEncode:

    def __init__(self):
        self.cmdCode = None

    def delCharFrame(self, addr, page, count):
        """
        删除指纹
        EF 01 FF FF FF FF 01 00 07 0C 01 F7 00 01 01 0D
        """
        self.cmdCode = CMDCode.delCharCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x07, 0x0C]
        addrArray = int2hex(addr, 4)
        pageArray = int2hex(page, 2)
        countArray = int2hex(count, 2)

        dataArray = typeArray + pageArray + countArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16

        return cmd


    def clrCharsFrame(self, addr):
        """
        清空指纹库
        EF 01 FF FF FF FF 01 00 03 0D 00 11
        """
        self.cmdCode = CMDCode.clrCharsCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x0D]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def readTempleteNumFrame(self, addr):
        """
        读有效指纹个数
        EF 01 FF FF FF FF 01 00 03 1D 00 21
        """
        self.cmdCode = CMDCode.readTempleteNumCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x1D]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def readIndexTableFrame(self, addr, page):
        """
        读索指纹引表PS_ReadIndexTable
        EF 01 FF FF FF FF 01 00 04 1F 00 00 24
        """
        self.cmdCode = CMDCode.readIndexTableCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x04, 0x1F]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray + [page]
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def checkPwdFrame(self, addr, pwd):
        """
        验证口令PS_VfyPwd
        EF 01 FF FF FF FF 01 00 07 13 00 00 00 00 00 1B
        """
        self.cmdCode = CMDCode.checkPwdCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x07, 0x13]
        addrArray = int2hex(addr, 4)
        pwdArray = int2hex(pwd, 4)

        dataArray = typeArray + pwdArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def getImageFrame(self, addr):
        """
        获取指纹图像
        EF 01 FF FF FF FF 01 00 03 01 00 05
        
        """
        self.cmdCode = CMDCode.getImageCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x01]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def genCharFrame(self, addr, bufId):
        """
        生成指纹特征
        EF 01 FF FF FF FF 01 00 04 02 01 00 08
        """
        self.cmdCode = CMDCode.genCharCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x04, 0x02]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray + [bufId]
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def regMBFrame(self, addr):
        """
        合并指纹
        EF 01 FF FF FF FF 01 00 03 05 00 09
        """
        self.cmdCode = CMDCode.regMBCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x05]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def storMBFrame(self, addr, bufId, page):
        """
        指纹存储
        EF 01 FF FF FF FF 01 00 06 06 01 00 03 00 11
        """
        self.cmdCode = CMDCode.storMBCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x06, 0x06]
        addrArray = int2hex(addr, 4)
        pageArray = int2hex(page, 2)

        dataArray = typeArray + [bufId] + pageArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd

    def searchMBFrame(self, addr, bufId, page, pageNum):
        """
        搜索指纹
        EF 01 FF FF FF FF 01 00 08 04 01 00 00 01 F4 01 03
        """
        self.cmdCode = CMDCode.searchMBCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x08, 0x04]
        addrArray = int2hex(addr, 4)
        pageArray = int2hex(page, 2)
        pageNumArray = int2hex(pageNum, 2)

        dataArray = typeArray + [bufId] + pageArray + pageNumArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd

    def uploadImgFrame(self, addr):
        """
        上传指纹图像
        EF 01 FF FF FF FF 01 00 03 0A 00 0E
        """
        self.cmdCode = CMDCode.uploadImgCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x0A]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd


    def readDevInfoFrame(self, addr):
        """
        读取系统基本参数
        EF 01 FF FF FF FF 01 00 03 16 00 1A
        
        """
        self.cmdCode = CMDCode.readDevInfoCmd
        head = [0xEF, 0x01]
        typeArray = [0x01, 0x00, 0x03, 0x16]
        addrArray = int2hex(addr, 4)

        dataArray = typeArray
        chk16 = CHK16(dataArray)
        cmd = head + addrArray + dataArray + chk16
        return cmd

    def getCmdCode(self):
        return self.cmdCode
