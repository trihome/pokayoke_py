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
import yaml

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
    CHANGERANGE = auto()
    CHANGERANGE_DONE = auto()


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

    # GPIO入力監視ポート
    __gpio_input = [21, 20, 16, 12]
    # 入力長押しタイマー
    __gpio_input_timer = []
    # GPIO入力監視ポート(I2C割込)
    __gpio_int = [7]

    # GPIO出力ポート
    __gpio_output = [26, 19, 13, 6]

    # メインステート
    __state_main = None

    # デバッグモード
    __debug = False

    # 点灯パターンのデフォルト値
    pattern = [0, 1, 2, 3]
    # パターンの進捗カウンタ
    __pattern_counter = 0
    # 現在点灯中のランプの点灯・点滅パターン
    __pattern_now_mode = 3

    # 設定ファイル名
    __setting_file = '/home/pi/gitwork/python/poka/config.yaml'

    def __init__(self, arg_verbose=False):
        """
        コンストラクタ
        Parameters
        ----------
        """
        pass
        if arg_verbose == True:
            # デバッグモードを有効化
            self.__debug = True

        # yaml形式設定ファイルを読み込み
        with open(self.__setting_file) as file:
            config = yaml.safe_load(file.read())
            # パターンを読み込み
            pattern = config["buttonrange"]
            if len(pattern) > 1:
                #読み込みが上手くいけば、パターンデータを置き換え
                self.pattern = pattern

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
            if self.__state_main == State_Main.CHANGERANGE:
                # 範囲設定モードの時、範囲確定に移る
                self.__state_main = State_Main.CHANGERANGE_DONE
            elif self.__state_main == State_Main.DO:
                # 運転中は何もしない
                pass
            else:
                # 運転状態に移行
                self.__state_main = State_Main.DO

        elif gpio_pin == self.__gpio_input[1]:
            # Bボタンが押された
            if self.__state_main == State_Main.DO:
                # 運転状態から一時停止状態に移行
                self.__state_main = State_Main.PAUSE

            # 長押し時間の指定
            time_nagaoshi = 0.7
            # 一時停止状態でBボタン押しっぱなしなら、長押し時間計測開始
            if (self.__state_main == State_Main.PAUSE) and (ch_val == 1):
                # 押されたとき、現在時間を保存
                self.__gpio_input_timer[self.__gpio_input.index(
                    gpio_pin)] = time.time()
            elif ch_val == 0:
                # 離されたとき、現在時間との差を計算
                div = time.time() - \
                    self.__gpio_input_timer[self.__gpio_input.index(gpio_pin)]
                if div > time_nagaoshi and div < time_nagaoshi * 5:
                    # 指定時間以上押されたらリセット状態に移行
                    self.__state_main = State_Main.RESET
        elif gpio_pin == self.__gpio_input[2] or gpio_pin == self.__gpio_input[3]:
            # 上下ボタンが押された
            # 一時停止状態の時
            if self.__state_main == State_Main.PAUSE:
                    # リセット状態に移行
                self.__state_main = State_Main.RESET
            elif self.__state_main == State_Main.DO:
                # 運転中は何もしない
                pass
            elif self.__state_main == State_Main.RESET:
                # リセット状態の時
                # 範囲変更モードに移行
                self.__state_main = State_Main.CHANGERANGE
                print(" MODE : CHANGERANGE")
            else:
                pass
        else:
            pass

        if self.__state_main == State_Main.CHANGERANGE:
            # 範囲変更モードのとき
            if gpio_pin == self.__gpio_input[2] and ch_val == 1:
                # 上ボタンが操作された
                if len(self.pattern) < 8:
                    # 範囲内である事を確認
                    # 最後の値を取り出し
                    val = self.pattern[-1]
                    # 最後の値に１を加算
                    val += 1
                    # パターンリストの最後に追加
                    self.pattern.append(val)
                    print(self.pattern)

            elif gpio_pin == self.__gpio_input[3] and ch_val == 1:
                # 下ボタンが押された
                if len(self.pattern) > 2:
                    # 範囲内である事を確認
                    # パターンリストの最後の値を削除
                    self.pattern.pop()
                    print(self.pattern)

    def SaveToSetting(self):
        """
        設定の保存
        """
        # 保存データの生成
        yml = {'buttonrange': self.pattern}
        # 書き込み
        with open(self.__setting_file, 'w') as file:
            yaml.dump(yml, file,default_flow_style=False)

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
            ioexp = IoExpI2C.IoExpI2C()

            # GPIO出力初期化
            gpioout = GpioOut.GpioOut(self.__gpio_output)

            # ステート初期化
            self.__state_main = State_Main.RESET

            # 立ち上がった事を示す点灯
            # 点灯範囲を示す
            for ch in self.pattern:
                ioexp.Update(ch, 3)
            time.sleep(2)
            ioexp.Flash()

            # メインループ
            while True:

                # I2C入力監視
                i2c_status = [0, 0, 0, 0, 0, 0, 0, 0]
                for port in self.__gpio_int:
                    if GPIO.input(port) == GPIO.LOW:
                        self.print(" I2C INT > GPIO [ %d ]" % port)
                        i2c_status = ioexp.Read()

                # ステート毎の処理
                if self.__state_main == State_Main.NONE:
                    self.print("State > NONE")
                    # リモコンランプを点灯
                    gpioout.Update(0, 0)
                    gpioout.Update(1, 1)
                    # IoExpを全消灯
                    ioexp.Update(9, 0)

                elif self.__state_main == State_Main.RESET:
                    # リセット状態
                    self.print("State > RESET")
                    # リモコンランプを点灯
                    gpioout.Update(0, 0)
                    gpioout.Update(1, 1)
                    # IoExpを全消灯
                    ioexp.Update(9, 0)
                    # パターンの進捗カウンタをリセット
                    self.__pattern_counter = 0
                    # 点灯・点滅パターンを初期値に戻す
                    self.__pattern_now_mode = 3

                elif self.__state_main == State_Main.PAUSE:
                    # 一時停止状態
                    self.print("State > PAUSE")
                    # リモコンランプを点灯
                    gpioout.Update(0, 0)
                    gpioout.Update(1, 3)

                elif self.__state_main == State_Main.CHANGERANGE:
                    # 範囲変更受付の状態
                    #self.print("State > CHANGERANGE")
                    # 範囲の数を数える
                    length = len(self.pattern)
                    # 設定されている範囲だけ点灯
                    for ch in range(length):
                        ioexp.Update(ch, 3)
                    # それ以外を消灯
                    for ch in range(length, 8):
                        ioexp.Update(ch, 0)
                elif self.__state_main == State_Main.CHANGERANGE_DONE:
                    # 範囲変更受付完了の状態
                    self.print("State > CHANGERANGE_DONE")
                    # 確定した範囲を示す点滅
                    for ch in self.pattern:
                        ioexp.Update(ch, 4)
                    time.sleep(1)
                    # フラッシュ
                    ioexp.Flash(1)
                    # 全消灯
                    ioexp.Update(9, 0)
                    # 保存
                    self.SaveToSetting()
                    # 状態を移行
                    self.__state_main = State_Main.RESET
                    pass
                elif self.__state_main == State_Main.DO:
                    # 運転中の状態
                    self.print("State > DO")
                    # リモコンランプを点灯
                    gpioout.Update(0, 1)
                    gpioout.Update(1, 0)
                    # パターンに応じて点灯
                    if self.__pattern_counter < len(self.pattern):
                        # カウンタがパターン数を超えてなければ
                        # 現在のパターンを読み出し
                        pattern_now = self.pattern[self.__pattern_counter]
                        # 対象を中速点滅
                        ioexp.Update(pattern_now,  self.__pattern_now_mode)
                    else:
                        # カウンタがパターン数を超えたら
                        # 一旦全点灯
                        for ch in self.pattern:
                            ioexp.Update(ch, 1)
                        time.sleep(0.5)
                        # フラッシュ
                        ioexp.Flash(1)
                        # 全消灯
                        ioexp.Update(9, 0)
                        time.sleep(0.5)
                        # パターンの進捗カウンタをリセット
                        self.__pattern_counter = 0
                        # IoExpを全消灯
                        ioexp.IoExpUpdate(9, 0)

                    # 対象のボタンが押されたかチェック
                    if i2c_status[pattern_now] == 1:
                        # 対象を点灯
                        ioexp.Update(pattern_now, 1)
                        # パターンの進捗カウンタをインクリメントし、次のパターン番号に移行
                        self.__pattern_counter += 1
                        # 点灯・点滅パターンを初期値に戻す
                        self.__pattern_now_mode = 3
                    elif (i2c_status[pattern_now] == 0) and (sum(i2c_status) > 0):
                        # 間違ったボタンを押した
                        # 対象を高速点滅に切替
                        self.__pattern_now_mode = 4
                    else:
                        pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            # IoExpを全消灯
            ioexp.IoExpUpdate(9, 0)
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
    # 引数Trueでデバッグモード
    main(False)
