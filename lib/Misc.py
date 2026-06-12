def CHK16(cmd):
    RX_CHX = 0

    for buf in cmd:
        RX_CHX += buf

    RX_CHX_L = RX_CHX & 0xff
    RX_CHX_H = RX_CHX >> 8 & 0xff

    return [RX_CHX_H, RX_CHX_L]


def int2hex(value, width):
    valArray = []
    i = 0
    while value > 0:
        valArray = [value & 0xFF] + valArray
        value = value >> 8
        i += 1
    less = width - i
    for i in range(less):
        valArray = [0x00] + valArray

    return valArray


def print_hex(bytes):
    l = [hex(int(i)) for i in bytes]
    print(" ".join(l), end='\r', flush=True)


def checkChk16(cmd):
    chk16 = CHK16(cmd[6:len(cmd) - 2])
    chk16Org = cmd[len(cmd) - 2:]
    if chk16 == chk16Org:
        return True

    return False
