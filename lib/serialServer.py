# -*- coding: utf-8 -*-
import sqlite3
import time

import serial
from PyQt5 import QtCore
from PyQt5.QtCore import QThread, QMutex

#from serverLog import LogHandler

#logger = LogHandler('serialServer')


class QuerySerial(object):
    """
    获取相应传感器的值
    """

    def __init__(self, port):
        self.port = port
        self.ser = serial.Serial(self.port, 9600, timeout=0.2)
        self.ser.flushInput()
        self.ser.flushOutput()

    def exec_cmd(self, command):
        """
        执行led控制
        :param command: 16进制值
        :return:
        """
        try:
            cmd = bytes.fromhex(command)
            # self.ser.reset_input_buffer()
            # self.ser.reset_output_buffer()
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(cmd)
            data = self.ser.read(8)
            # logger.debug('4150_data: ' + str(data.hex()))
        except Exception as e:
            logger.error('4150_data error: ' + str(e))

    def turn_on_red(self):
        """
        开启红灯
        :return:
        """
        command = '01 05 00 10 FF 00 8D FF'
        self.exec_cmd(command)

    def turn_off_red(self):
        """
        关闭红灯
        :return:
        """
        command = '01 05 00 10 00 00 CC 0F'
        self.exec_cmd(command)

    def turn_on_yellow(self):
        """
        开启黄灯
        :return:
        """
        command = '01 05 00 11 FF 00 DC 3F'
        self.exec_cmd(command)

    def turn_off_yellow(self):
        """
        关闭黄灯
        :return:
        """
        command = '01 05 00 11 00 00 9D CF'
        self.exec_cmd(command)

    def turn_on_green(self):
        """
        开启绿灯
        :return:
        """
        command = '01 05 00 12 FF 00 2C 3F'
        self.exec_cmd(command)

    def turn_off_green(self):
        """
        关闭绿灯
        :return:
        """
        command = '01 05 00 12 00 00 6D CF'
        self.exec_cmd(command)

    def turn_on_door(self):
        """
        开门
        :return:
        """
        command = '01 05 00 13 FF 00 7D FF'
        self.exec_cmd(command)

    def turn_off_door(self):
        """
        关门
        :return:
        """
        command = '01 05 00 13 00 00 3C 0F'
        self.exec_cmd(command)

    def turn_on_buzzer(self):
        """
        打开蜂鸣器
        :return:
        """
        command = '01 05 00 14 FF 00 CC 3E'
        self.exec_cmd(command)

    def turn_off_buzzer(self):
        """
        关闭蜂鸣器
        :return:
        """
        command = '01 05 00 14 00 00 8D CE'
        self.exec_cmd(command)

    def get_beam_data(self, command='0C 03 00 00 00 02 C5 16'):
        """
        查询光照强度
        :param command:
        :return:
        """
        try:
            cmd = bytes.fromhex(command)
            # self.ser.reset_input_buffer()
            # self.ser.reset_output_buffer()
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(cmd)
            data = self.ser.read(9)
            logger.debug('beam_data: ' + str(data.hex()))
            data = str(data.hex())
            if data[0:2] == '0c':
                beam_var = int('0x' + data[6:14], 16)
                logger.debug('beam_var: ' + str(beam_var))
                return beam_var
            else:
                return None
        except Exception as e:
            logger.error('beam_data error: ' + str(e))
            return None

    def fan_power_on(self):
        """
        风扇上电
        :return:
        """
        command = '01 05 00 15 FF 00 9D FE'
        self.exec_cmd(command)
        time.sleep(0.5)

    def fan_power_off(self):
        """
        风扇断电
        :return:
        """
        command = '01 05 00 15 00 00 DC 0E'
        self.exec_cmd(command)

    def fan_high_level(self):
        """
        风扇高电平
        :return:
        """
        command = '01 05 00 16 FF 00 6D FE'
        self.exec_cmd(command)

    def fan_low_level(self):
        """
        风扇低电平
        :return:
        """
        command = '01 05 00 16 00 00 2C 0E'
        self.exec_cmd(command)

    def open_fan(self):
        """
        打开风扇的脉冲信号
        :return:
        """
        self.fan_high_level()
        time.sleep(0.3)
        self.fan_low_level()

    def open_ambiance_lamp(self):
        """
        打开风扇的气氛灯脉冲信号
        :return:
        """
        self.fan_high_level()
        time.sleep(1)
        self.fan_low_level()

    def get_body_di_data(self, command='01 01 00 00 00 07 7D C8'):
        """
        获取继电器DI的值，人体传感通过DI口，获取状态值
        :param command: 16进制值
        :return:
        """
        try:
            cmd = bytes.fromhex(command)
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(cmd)
            data = self.ser.read(6)
            data = str(data.hex())
            if data[0:6] == '010101':
                status_var = int('0x' + data[6:8], 16)
                logger.debug('body_data_status: ' + str(status_var))
                return status_var
            else:
                return None
        except Exception as e:
            logger.error('body_data error: ' + str(e))
            return None

    def get_led_do_data(self):
        """
        获取继电器DO的值，灯光通过DO口获取状态值
        :param command: 16进制值
        :return:
        """
        try:
            command = '01 01 00 10 00 08 3C 09'
            cmd = bytes.fromhex(command)
            # self.ser.reset_input_buffer()
            # self.ser.reset_output_buffer()
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(cmd)
            data = self.ser.read(6)
            logger.debug('Do_data: ' + str(data.hex()))
            data = str(data.hex())
            status_var = int('0x' + data[6:8], 16)
            logger.debug('Do_status: ' + str(status_var))
            return status_var
        except Exception as e:
            logger.error('Do_data error: ' + str(e))
            return None

    def create_led_table(self):
        create_led = 'create table led(id integer primary key,  red integer, yellow integer, green integer, door integer, fan integer)'
        sql_cmd = 'insert into led (red, yellow, green, door, fan) values (0, 0, 0, 0, 0)'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(create_led)
            conn.commit()
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def create_livingroom_table(self):
        create_living = 'create table living(id integer primary key, yellow integer, door integer, fan integer)'
        sql_cmd = 'insert into living (yellow, door, fan) values (0, 0, 0)'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(create_living)
            conn.commit()
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def set_sql_led_status(self, dev):
        if dev == 'red_on':
            sql_cmd = 'UPDATE led SET red = 1;'
        elif dev == 'red_off':
            sql_cmd = 'UPDATE led SET red = 0;'
        elif dev == 'yellow_on':
            sql_cmd = 'UPDATE led SET yellow = 1;'
        elif dev == 'yellow_off':
            sql_cmd = 'UPDATE led SET yellow = 0;'
        elif dev == 'green_on':
            sql_cmd = 'UPDATE led SET green = 1;'
        elif dev == 'green_off':
            sql_cmd = 'UPDATE led SET green = 0;'
        elif dev == 'door_on':
            sql_cmd = 'UPDATE led SET door = 1;'
        elif dev == 'door_off':
            sql_cmd = 'UPDATE led SET door = 0;'
        elif dev == 'fan_on':
            sql_cmd = 'UPDATE led SET fan = 1;'
        elif dev == 'fan_off':
            sql_cmd = 'UPDATE led SET fan = 0;'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def get_sql_led_status(self):
        sql_cmd = 'select * from led;'
        res_list = []
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            led_status = cursor.execute(sql_cmd)
            for row in led_status:
                res_list.append(row)
            conn.commit()
        except Exception as e:
            res_list = []
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()
        return res_list

    def reset_sql_led_status(self):
        sql_cmd = 'UPDATE led SET fan = 0, red = 0, yellow = 0, green = 0, door = 0;'
        sql_cmd2 = 'UPDATE living SET fan = 0, yellow = 0, door = 0;'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(sql_cmd)
            cursor.execute(sql_cmd2)
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def reset(self):
        """
        复位AiOT器件
        :return:
        """
        self.turn_off_green()
        time.sleep(0.05)
        self.turn_off_buzzer()
        time.sleep(0.05)
        self.fan_power_off()
        time.sleep(0.05)
        self.turn_off_yellow()
        time.sleep(0.05)
        self.turn_off_red()
        time.sleep(0.05)
        self.turn_off_door()
        time.sleep(0.05)
        self.reset_sql_led_status()

    def close_serial(self):
        """
        关闭串口
        :return:
        """
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.close()
        except Exception as e:
            print(e)


class TempQuerySerial(object):
    """
    获取相应传感器的值
    """

    def __init__(self, port):
        self.port = port
        self.ser = serial.Serial(self.port, 9600, timeout=0.2)

    def get_temp(self, command='5A 01 00 5B'):
        try:
            cmd = bytes.fromhex(command)  # 查询地址转换成byte类型
            self.ser.write(cmd)  # 将查询命令写入串口
            data = self.ser.read(9)  # 读取串口的返回值，具体的根据传感器的相关文档，填入数据长度
            data = str(data.hex())
            temp_var = int('0x' + data[12:16], 16) / 10 + 0.2
            temp_var = '{:.1f}'.format(temp_var)
            # print(temp_var)
            return temp_var
        except Exception as e:
            logger.error('data error: ' + str(e))
            return None

    def close_serial(self):
        """
        关闭串口
        :return:
        """
        self.ser.close()


class NewQuerySerial(object):
    """
    获取相应传感器的值
    """

    def __init__(self, port):
        self.port = port
        self.ser = serial.Serial(self.port, 9600, timeout=0.2)
        self.ser.flushInput()
        self.ser.flushOutput()

    def exec_cmd(self, command):
        """
        执行led控制
        :param command: 16进制值
        :return:
        """
        try:
            cmd = bytes.fromhex(command)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write(cmd)
        except Exception as e:
            logger.error('4150_data error: ' + str(e))

    def turn_on_fan(self):
        """
        开启风扇,四路
        :return:
        """
        # print('打开风扇')
        command = 'FE 05 00 03 FF 00 68 35'
        self.exec_cmd(command)

    def turn_off_fan(self):
        """
        关闭风扇
        :return:
        """
        # print('关闭风扇')
        command = 'FE 05 00 03 00 00 29 C5'
        self.exec_cmd(command)

    def turn_on_red(self):
        """
        开启红灯 三路
        :return:
        """
        # print('打开黄灯')
        command = 'FE 05 00 02 FF 00 39 F5'
        self.exec_cmd(command)

    def turn_off_red(self):
        """
        关闭红灯
        :return:
        """
        # print('关闭黄灯')
        command = 'FE 05 00 02 00 00 78 05'
        self.exec_cmd(command)

    def turn_on_yellow(self):
        """
        开启黄灯 二路
        :return:
        """
        # print('打开绿灯')
        command = 'FE 05 00 01 FF 00 C9 F5'
        self.exec_cmd(command)

    def turn_off_yellow(self):
        """
        关闭黄灯
        :return:
        """
        # print('关闭绿灯')
        command = 'FE 05 00 01 00 00 88 05'
        self.exec_cmd(command)

    def turn_on_green(self):
        """
        打开绿灯 一路
        :return:
        """
        # print('打开红灯')
        command = 'FE 05 00 00 FF 00 98 35'
        self.exec_cmd(command)

    def turn_off_green(self):
        """
        关闭绿灯
        :return:
        """
        # print('关闭红灯')
        command = 'FE 05 00 00 00 00 D9 C5'
        self.exec_cmd(command)

    def create_led_table(self):
        create_led = 'create table led(id integer primary key,  red integer, yellow integer, green integer, door integer, fan integer)'
        sql_cmd = 'insert into led (red, yellow, green, door, fan) values (0, 0, 0, 0, 0)'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(create_led)
            conn.commit()
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def create_livingroom_table(self):
        create_living = 'create table living(id integer primary key, yellow integer, door integer, fan integer)'
        sql_cmd = 'insert into living (yellow, door, fan) values (0, 0, 0)'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(create_living)
            conn.commit()
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def set_sql_led_status(self, dev):
        if dev == 'red_on':
            sql_cmd = 'UPDATE led SET red = 1;'
        elif dev == 'red_off':
            sql_cmd = 'UPDATE led SET red = 0;'
        elif dev == 'yellow_on':
            sql_cmd = 'UPDATE led SET yellow = 1;'
        elif dev == 'yellow_off':
            sql_cmd = 'UPDATE led SET yellow = 0;'
        elif dev == 'green_on':
            sql_cmd = 'UPDATE led SET green = 1;'
        elif dev == 'green_off':
            sql_cmd = 'UPDATE led SET green = 0;'
        elif dev == 'door_on':
            sql_cmd = 'UPDATE led SET door = 1;'
        elif dev == 'door_off':
            sql_cmd = 'UPDATE led SET door = 0;'
        elif dev == 'fan_on':
            sql_cmd = 'UPDATE led SET fan = 1;'
        elif dev == 'fan_off':
            sql_cmd = 'UPDATE led SET fan = 0;'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(sql_cmd)
            conn.commit()
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def get_sql_led_status(self):
        sql_cmd = 'select * from led;'
        res_list = []
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            led_status = cursor.execute(sql_cmd)
            for row in led_status:
                res_list.append(row)
            conn.commit()
        except Exception as e:
            res_list = []
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()
        return res_list

    def reset_sql_led_status(self):
        sql_cmd = 'UPDATE led SET fan = 0, red = 0, yellow = 0, green = 0, door = 0;'
        sql_cmd2 = 'UPDATE living SET fan = 0, yellow = 0, door = 0;'
        conn = sqlite3.connect("face.db")
        # 创建一个游标 curson
        cursor = conn.cursor()
        try:
            cursor.execute(sql_cmd)
            cursor.execute(sql_cmd2)
        except Exception as e:
            pass
        # 执行提交的操作
        conn.commit()
        # 关闭游标
        cursor.close()
        # 关闭数据库
        conn.close()

    def reset(self):
        """
        复位AiOT器件
        :return:
        """
        self.turn_off_green()
        time.sleep(0.05)
        self.turn_off_yellow()
        time.sleep(0.05)
        self.turn_off_red()
        time.sleep(0.05)
        self.turn_off_fan()
        time.sleep(0.05)

    def close_serial(self):
        """
        关闭串口
        :return:
        """
        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.close()
        except Exception as e:
            print(e)

    def confirm_device(self):
        self.turn_on_green()
        time.sleep(0.05)
        self.turn_on_yellow()
        time.sleep(0.05)
        self.turn_on_red()
        time.sleep(0.05)
        self.turn_on_fan()
        time.sleep(0.05)
