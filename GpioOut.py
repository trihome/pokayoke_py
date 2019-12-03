#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-
# -----------------------------------------------
# GPIO Output Class
#
# The MIT License (MIT)
# Copyright (C) 2019 myasu.
# -----------------------------------------------

import time
import RPi.GPIO as GPIO
import smbus
import threading


class GpioOut():
    """
    GPIO Output
    """
    # ------------------------
    # メンバ定数
    # ------------------------

    #点滅速度（間隔sec）
    __INTERVAL = 0.15

    # ------------------------
    # メンバ変数
    # ------------------------

    # ピン番号
    __GpioPin = []
    # GPIOの出力ステータス
    # 0:消灯、1:点灯、2:点滅（長）、3:点滅（中）、4:点滅（短）
    __GpioStatus = []

    # 点滅カウンタ
    __blink = 0

    # ------------------------
    # メンバ関数
    # ------------------------

    def __init__(self, arg_Pin, arg_verbose=False):
        """
        コンストラクタ
        Parameters
        ----------
        argPin : int
            出力ピン番号
        arg_verbose:bool
            メッセージの強制表示
        """
        pass
        # 引数に渡されたピン番号をプロパティに代入
        self.__GpioPin = arg_Pin

        # GPIO初期化
        GPIO.setmode(GPIO.BCM)
        self.__GpioStatus = []
        for item in self.__GpioPin:
            # ピンを出力設定
            GPIO.setup(item, GPIO.OUT)
            # 制御対象のピン番号のステータスを初期化
            self.__GpioStatus.append(0)

        # 点滅制御用スレッド
        thread_1 = threading.Thread(target=self.event_Thread)
        thread_1.daemon = True
        thread_1.start()

    def __del__(self):
        """
        デストラクタ
        """
        pass
        # GPIOを解放
        GPIO.cleanup()

    def event_Thread(self):
        """
        スレッド・ランプ出力の点滅
        """
        while True:
            # 点滅パターン計算
            # 毎回
            pattern_1 = self.__blink >> 0 & 0b1
            # 2回に一回
            pattern_2 = self.__blink >> 1 & 0b1
            # 4回に一回
            pattern_3 = self.__blink >> 2 & 0b1

            # 長点滅の処理
            if pattern_3 == 1:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 2:
                        GPIO.output(self.__GpioPin[i], 1)
            else:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 2:
                        GPIO.output(self.__GpioPin[i], 0)

            # 中点滅の処理
            if pattern_2 == 1:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 3:
                        GPIO.output(self.__GpioPin[i], 1)
            else:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 3:
                        GPIO.output(self.__GpioPin[i], 0)

            # 短点滅の処理
            if pattern_1 == 1:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 4:
                        GPIO.output(self.__GpioPin[i], 1)
            else:
                for i in range(len(self.__GpioPin)):
                    if self.__GpioStatus[i] == 4:
                        GPIO.output(self.__GpioPin[i], 0)

            # 点滅カウンタ
            self.__blink += 1
            if self.__blink > 7:
                self.__blink = 0

            # ウェイト
            time.sleep(self.__INTERVAL)

    def Update(self, arg_ch, arg_val):
        """
        GPIO出力状態の更新
        Parameters
        ----------
        arg_ch : 
            ch番号
            (出力ピン番号のリストで指定した順番。0から始まる値で指定)
        arg_val : 
            点灯条件値
            （0:消灯、1:点灯、2:点滅（長）、3:点滅（中）、4:点滅（短））
        """
        if arg_ch < len(self.__GpioPin):
            # 受け取ったポート番号が、配列長を超えていないこと
            if arg_val == 0:
                # 指定の番号をOFF
                GPIO.output(self.__GpioPin[arg_ch], 0)
                # 点灯ステータスの変更
                self.__GpioStatus[arg_ch] = 0
            elif arg_val == 1:
                # 指定の番号をON
                GPIO.output(self.__GpioPin[arg_ch], 1)
                # 点灯ステータスの変更
                self.__GpioStatus[arg_ch] = 1
            elif arg_val == 2:
                # 指定の番号を点滅・長
                # 点灯ステータスの変更
                self.__GpioStatus[arg_ch] = 2
                pass
            elif arg_val == 3:
                # 指定の番号を点滅・中
                # 点灯ステータスの変更
                self.__GpioStatus[arg_ch] = 3
                pass
            elif arg_val == 4:
                # 指定の番号を点滅・短
                self.__GpioStatus[arg_ch] = 4
                pass
            else:
                pass
        elif arg_ch == 99:
            # ポート99番を指定されたときは、全ポートを同時操作
            for i in self.__GpioPin:
                if arg_val == 1:
                    # 全てON
                    GPIO.output(i, 1)
                else:
                    # 全てOFF
                    GPIO.output(i, 0)
        else:
            # それ以外の時はエラー
            print("Port %s is not found." % (arg_port))
