#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-
# -----------------------------------------------
# POKAYOKE System (Python Edition)
#
# The MIT License (MIT)
# Copyright (C) 2019 myasu.
# -----------------------------------------------

import time
import RPi.GPIO as GPIO
from enum import Enum, auto
from datetime import datetime

import GpioOut
import IoExpI2C


class State_Main(Enum):
    """
    メイン処理のステータス
    """
    NONE = auto()
    RESET = auto()
    PAUSE = auto()
    DO = auto()


def test_out():
    """
    GPIOランプ点灯テスト
    """
    port = [26, 19, 13, 6]
    out = GpioOut.GpioOut(port)
    # 点滅
    print("-- LAMP TEST GPIO --")
    for mode in [1, 2, 3, 4, 0]:
        print(" > MODE %d" % (mode))
        for ch in range(len(port)):
            out.Update(ch, mode)
        time.sleep(3.0)


def test_i2cout():
    """
    i2cランプ点灯テスト
    """
    out = IoExpI2C.IoExpI2C()
    print("-- LAMP TEST I2C --")

    # 直接点灯（流星）
    for i in range(8):
        out.IoExpUpdate(i, 1)
        time.sleep(0.05)
    for i in range(8):
        out.IoExpUpdate(i, 0)
        time.sleep(0.05)

    # 点滅
    for mode in [1, 2, 3, 4, 0]:
        print(" > MODE %d" % (mode))
        for ch in range(8):
            out.Update(ch, mode)
        time.sleep(3.0)


class Main():
    """
    メイン処理クラス
    """

    # 入力監視ポート
    __gpio_input = [21, 20, 16, 12]
    # 入力長押しタイマー
    __gpio_input_timer = []
    # 入力監視ポート(I2C割込)
    __gpio_int = [7]

    # メインステート
    __state_main = None

    #デバッグモード
    __debug = False

    def __init__(self, arg_verbose=False):
        """
        コンストラクタ
        Parameters
        ----------
        """
        pass
        if arg_verbose == True:
            #デバッグモードを有効化
            self.__debug = True

    def print(self, arg_message, arg_err=False):
        """
        デバッグ用メッセージ
        """
        if self.__debug == True:
            print(" > %s" % (arg_message))

    def event_callback_gpio(self, gpio_pin):
        """
        GPIO入力コールバック
        """
        # 該当ポートの値読み込み
        ch_val = GPIO.input(gpio_pin)
        self.print(" Callback > GPIO [ %d ] > %d" % (gpio_pin, ch_val))

        # メインステートの変更
        if gpio_pin == self.__gpio_input[0]:
            # Aボタンが押された
            # 運転状態に移行
            self.__state_main = State_Main.DO

        elif gpio_pin == self.__gpio_input[1]:
            # Bボタンが押された
            if self.__state_main == State_Main.DO:
                # 運転状態から一時停止状態に移行
                self.__state_main = State_Main.PAUSE

            # 一時停止状態で押しっぱなしなら、長押し時間計測開始
            if (self.__state_main == State_Main.PAUSE) and (ch_val == 1):
                # 押されたとき、現在時間を保存
                self.__gpio_input_timer[self.__gpio_input.index(
                    gpio_pin)] = time.time()
            elif ch_val == 0:
                # 離されたとき、現在時間との差を計算
                div = time.time() - \
                    self.__gpio_input_timer[self.__gpio_input.index(gpio_pin)]
                if div > 0.7 and div < 3:
                    # 指定時間以上押されたらリセット状態に移行
                    self.__state_main = State_Main.RESET
        else:
            pass

    def Do(self):
        """
        メイン処理
        """
        try:
            # GPIO初期化
            GPIO.setmode(GPIO.BCM)
            # GPIO入力設定
            for port in self.__gpio_input:
                # プルアップ抵抗を有効化
                GPIO.setup(port, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                # コールバック設定（立ち上がり/立ち下がり）
                GPIO.add_event_detect(
                    port, GPIO.BOTH, callback=self.event_callback_gpio, bouncetime=100)
                # 長押しタイマー初期化
                self.__gpio_input_timer.append(0)

            # GPIO入力設定（I2C割込）
            for port in self.__gpio_int:
                # プルアップ抵抗を有効化（メインループ中の監視で誤動作少なくなる）
                GPIO.setup(port, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # I2C初期化
            i2cin = IoExpI2C.IoExpI2C()

            # ステート初期化
            self.__state_main = State_Main.NONE

            # メインループ
            while True:

                # I2C入力監視
                for port in self.__gpio_int:
                    if GPIO.input(port) == GPIO.LOW:
                        self.print(" I2C INT > GPIO [ %d ]" % port)
                        i2cin.Read()

                #ステート毎の処理
                if self.__state_main == State_Main.NONE:
                    self.print("State > NONE")
                elif self.__state_main == State_Main.RESET:
                    self.print("State > RESET")
                elif self.__state_main == State_Main.PAUSE:
                    self.print("State > PAUSE")
                elif self.__state_main == State_Main.DO:
                    self.print("State > DO")

                time.sleep(0.01)

        except KeyboardInterrupt:

            # コールバック解放処理
            for port in self.__gpio_input:
                GPIO.remove_event_detect(port)
            GPIO.cleanup()
        finally:
            pass


def main(args=None):
    """
    メイン関数
    Parameters
    ----------
    """
    do = Main(args)
    do.Do()



if __name__ == '__main__':
    main(True)
