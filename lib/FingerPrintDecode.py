from enum import Enum

from lib.Misc import *


def checkChk16(cmd):
    """
    Chk16计算
    """
    try:
        chk16 = CHK16(cmd[6:len(cmd) - 2])
        chk16Org = cmd[len(cmd) - 2:]
        if chk16[0] == chk16Org[0] and chk16[1] == chk16Org[1]:
            return True

        return False
    except:
        return False


def isFingerFinded(cmd):
    """
    是否匹配到指纹
    """
    if checkChk16(cmd):
        return cmd[9] == 0

    return False

def getTempleteNum(cmd):
    """
    计算模版总是
    """
    count = 0
    if checkChk16(cmd):
        if cmd[9] == 0:
            count = cmd[11]
            count += cmd[10] << 8

    return count


def getTempleteArray(cmd, page):
    """
    计算模版列表，返回模版列表索引id
    """
    templeteArray = []
    if checkChk16(cmd):
        if cmd[9] == 0:
            len = cmd[8]
            len += cmd[7] << 8
            byteId = 0
            for byte in cmd[10:len + 7]:
                if byte != 0x00:
                    for i in range(8):
                        hasTemplete = (byte >> i) & 0x01
                        if hasTemplete != 0:
                            templeteArray = templeteArray + [page * 256 + byteId * 8 + i]
                byteId += 1

    return templeteArray


class SearchCharRst(Enum):
    """
    指纹特征值匹配结果枚举
    """
    found = 0
    error = 1
    empty = 9


def searchMB(cmd):
    """
    指纹特征值匹配结果获取
    返回
        [识别结果，指纹模版ID，置信度]
    """
    resultArray = []
    if checkChk16(cmd):
        if cmd[9] == SearchCharRst.found.value:
            resultArray += [SearchCharRst.found.value]
        elif cmd[9] == SearchCharRst.empty.value:
            resultArray += [SearchCharRst.empty.value]
        else:
            resultArray += [SearchCharRst.error.value]
        charId = cmd[11]
        charId += cmd[10] << 8
        resultArray += [charId]
        try:
            score = cmd[13]
            score += cmd[12] << 8
        except:
            score = 0
        resultArray += [score]

    return resultArray
