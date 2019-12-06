#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-
# -----------------------------------------------
# IO Expander (MCP23017) Control Class
#
# The MIT License (MIT)
# Copyright (C) 2019 myasu.
# -----------------------------------------------

import smbus
import threading
import time


# ------------------------
# 定数
# ------------------------

# IOExpanderボードのピン配置（変更不可）
CHANNEL = 1  # i2c割り当てチャンネル 1 or 0
REG_IODIRA_INOUT = 0x00  # Aポート側設定（1:入力、0:出力）
REG_IODIRB_INOUT = 0xff  # Bポート側設定（1:入力、0:出力）
ICADDR_DEFAULT = 0x20   # スレーブ側ICアドレス

# MCP23017 入出力設定レジスタ（変更不可）
# http://kzhishu.hatenablog.jp/entry/2016/07/19/090000
# https://qazsedcftf.blogspot.com/2019/04/esp32arduinomcp23017.html
# https://www.tnksoft.com/blog/?p=4713
REG_IODIRA = 0x00  # ■■■入出力方向
REG_IODIRB = 0x01  # (0: 出力  1:入力)
REG_IPOLA = 0x02  # ■■■I/O 極性
REG_IPOLB = 0x03  # (0: 0='L', 1='H' ; 1: 1='L', 0='H')
REG_GPINTENA = 0x04  # ■■■状態変化割り込み
REG_GPINTENB = 0x05  # (0:無効 1:有効)
REG_DEFVALA = 0x06  # ■■■状態変化割り込みの規定値
REG_DEFVALB = 0x07  # (この値と逆になったら割り込み発生)
REG_INTCONA = 0x08  # ■■■状態変化割り込みの比較値
REG_INTCONB = 0x09  # (0: 前の値と比較  1:DEFV の値と比較)
REG_IOCONA = 0x0a  # ■■■コンフィグレーションレジスタ※
REG_IOCONB = 0x0b  #
REG_GPPUA = 0x0c  # ■■■プルアップ制御
REG_GPPUB = 0x0d  # (0: プルアップ無効  1:プルアップ有効)
REG_INTFA = 0x0e  # ■■■割込みフラグレジスタ (INTCAP 又は GPIO リードでクリア)
REG_INTFB = 0x0f  # (0: 割り込みなし  1:割り込み発生)
REG_INTCAPA = 0x10  # ■■■割込みキャプチャレジスタ
REG_INTCAPB = 0x11  # (割込み発生時の GPIO の値)
REG_GPIOA = 0x12  # ■■■出力レジスタ
REG_GPIOB = 0x13  # (GPIOの値)
REG_OLATA = 0x14  # ■■■出力ラッチレジスタ
REG_OLATB = 0x15  # (出力ラッチの値)
'''
※IOCON 内容
bit 7     BANK    レジスタのアドレス指定を制御する
    1 = 各ポートに関連付けられているレジスタが別々のバンクに分かれる
    0 = レジスタが全部同じバンクに入れられる( アドレスが連続した状態)
bit 6     MIRROR    INT ピンのMirror ビット
    1 = INT ピン同士を内部接続する
    0 = INT ピン同士を接続しない。
        INTA はPORTA に関連付けられ、INTB はPORTB に関連付けられる。
bit 5     SEQOP    シーケンシャル動作モードビット
    1 = シーケンシャル動作が無効になり、アドレスポインタはインクリメントされない
    0 = シーケンシャル動作が有効になり、アドレスポインタがインクリメントされる
bit 4     DISSLW    SDA 出力のスルーレート制御ビット
    1 = スルーレートは無効
    0 = スルーレートは有効
bit 3    HAEN    ハードウェア アドレス イネーブル ビット(MCP23S17 のみ)
    MCP23017は値に関わらず、アドレスピンは常に有効。
bit 2    ODR    INT ピンをオープンドレイン出力として設定する
    1 = オープンドレイン出力(INTPOL ビットよりも優先される)
    0 = アクティブ ドライバ出力( 極性はINTPOL ビットで設定する)
bit 1    INTPOL    このビットでINT 出力ピンの極性を設定する
    1 = アクティブHigh
    0 = アクティブLow
bit 0     未実装    0」として読み出し
尚、BANK を変更すると、アドレスマッピングが変更されるため、注意の事。
( 1バイトアクセスでライトすること。)
'''

# IOExpanderボードのch対応付け（変更可）
# BEGIN_IN_DEFAULT = 0  # GPIO I2C入力の先頭ch番号
# BEGIN_OUT_DEFAULT = 0  # GPIO I2C出力の先頭ch番号


class IoExpI2C():
    """
    IO Expander (MCP23017) Control Class
    """
    # ------------------------
    # メンバ定数
    # ------------------------

    # 点滅速度（間隔sec）
    __INTERVAL = 0.15

    # ------------------------
    # メンバ変数
    # ------------------------

    # GPIOの出力ステータス
    # 0:消灯、1:点灯、2:点滅（長）、3:点滅（中）、4:点滅（短）
    __GpioStatus = [0, 0, 0, 0, 0, 0, 0, 0]

    # 点滅カウンタ
    __blink = 0

    # ------------------------
    # メンバ関数
    # ------------------------

    def __init__(self, arg_icaddr=ICADDR_DEFAULT, arg_verbose=False):
        '''
        初期化
        Parameters
        ----------
        arg_icaddr : int
            I2Cアドレス
        arg_verbose: bool
            メッセージの強制表示
        '''
        # 定数の設定
        self.__ICADDR = arg_icaddr

        # IoExpander ICの初期化
        # I2Cの設定
        self.bus = smbus.SMBus(CHANNEL)
        # PORTAの設定
        self.bus.write_byte_data(
            self.__ICADDR, REG_IOCONA, 0b00000110)  # コンフィグ
        self.bus.write_byte_data(
            self.__ICADDR, REG_IODIRA, REG_IODIRA_INOUT)  # 入出力
        # PORTBの設定
        self.bus.write_byte_data(
            self.__ICADDR, REG_IOCONB, 0b00000110)  # コンフィグ
        self.bus.write_byte_data(
            self.__ICADDR, REG_IODIRB, REG_IODIRB_INOUT)  # 入出力
        self.bus.write_byte_data(
            self.__ICADDR, REG_GPPUB, REG_IODIRB_INOUT)  # プルアップ
        self.bus.write_byte_data(
            self.__ICADDR, REG_GPINTENB, REG_IODIRB_INOUT)  # 割込

        # 点滅制御用スレッド
        thread_1 = threading.Thread(target=self.event_Thread)
        thread_1.daemon = True
        thread_1.start()

    def __del__(self):
        """
        デストラクタ
        """
        pass

    def print(self, arg_message, arg_err=False):
        """
        デバッグ用メッセージ
        """
        if self.__debug == True:
            print(" > %s" % (arg_message))

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
                for i in range(8):
                    if self.__GpioStatus[i] == 2:
                        self.IoExpUpdate(i, 1)
            else:
                for i in range(8):
                    if self.__GpioStatus[i] == 2:
                        self.IoExpUpdate(i, 0)

            # 中点滅の処理
            if pattern_2 == 1:
                for i in range(8):
                    if self.__GpioStatus[i] == 3:
                        self.IoExpUpdate(i, 1)
            else:
                for i in range(8):
                    if self.__GpioStatus[i] == 3:
                        self.IoExpUpdate(i, 0)

            # 短点滅の処理
            if pattern_1 == 1:
                for i in range(8):
                    if self.__GpioStatus[i] == 4:
                        self.IoExpUpdate(i, 1)
            else:
                for i in range(8):
                    if self.__GpioStatus[i] == 4:
                        self.IoExpUpdate(i, 0)

            # 点滅カウンタ
            self.__blink += 1
            if self.__blink > 7:
                self.__blink = 0

            # ウェイト
            time.sleep(self.__INTERVAL)

    def Flash(self, arg_mode=0):
        """
        フラッシュ（流星）点灯
        Parameters
        ----------
        arg_mode :
            点灯パターン(0:流星、1:点滅)
        """
        if arg_mode == 0:
            # 流星左～右
            for i in range(8):
                self.IoExpUpdate(i, 1)
                time.sleep(0.03)
            for i in range(8):
                self.IoExpUpdate(i, 0)
                time.sleep(0.03)
        elif arg_mode == 1:
            # 流星右～左
            for i in range(8):
                self.IoExpUpdate(8 - i, 1)
                time.sleep(0.03)
            for i in range(8):
                self.IoExpUpdate(8 - i, 0)
                time.sleep(0.03)
        elif arg_mode == 2:
            # 点滅
            for j in range(4):
                for i in range(8):
                    self.IoExpUpdate(i, 1)
                time.sleep(0.08)
                for i in range(8):
                    self.IoExpUpdate(i, 0)
                time.sleep(0.08)
        else:
            pass

        pass

    def Update(self, arg_ch, arg_val):
        """
        出力状態の更新
        Parameters
        ----------
        arg_ch : 
            ch番号(0から始まる値で指定)
            (ポート9番を指定されたときは、全ポートを同時操作)
        arg_val : 
            点灯条件値
            （0:消灯、1:点灯、2:点滅（長）、3:点滅（中）、4:点滅（短））
        """
        if arg_val < 5:
            # 受け取った点灯条件値が、5を超えていないこと
            if arg_ch < 8:
                # 受け取ったポート番号が、8を超えていないこと
                if arg_val == 0:
                    # 指定の番号をOFF
                    self.IoExpUpdate(arg_ch, 0)
                    # 点灯ステータスの変更
                    self.__GpioStatus[arg_ch] = 0
                elif arg_val == 1:
                    # 指定の番号をON
                    self.IoExpUpdate(arg_ch, 1)
                    # 点灯ステータスの変更
                    self.__GpioStatus[arg_ch] = 1
                elif arg_val >= 2 and arg_val <= 4:
                    # 指定の番号を点滅・長・中・短
                    # 点灯ステータスの変更
                    self.__GpioStatus[arg_ch] = arg_val
                else:
                    pass
            elif arg_ch == 9:
                # ポート9番を指定されたときは、全ポートを同時操作
                for ch in range(8):
                    # 指定の番号をON
                    self.IoExpUpdate(ch, arg_val)
                    # 点灯ステータスの変更
                    self.__GpioStatus[ch] = arg_val
            else:
                # それ以外の時はエラー
                self.print("Port %s is not found." % (arg_ch))
        else:
            # それ以外の時はエラー
            self.print("val error %d." % (arg_ch))

    def IoExpUpdate(self, arg_ch, arg_val):
        """
        IoExpander出力
        （この関数は直接呼び出さないこと。Update関数を使って下さい）
        Parameters
        ----------
        arg_ch : 
            ch番号(0から始まる値で指定)
        arg_val : 
            点灯条件値
            （0:消灯、1:点灯）
        """
        port = arg_ch
        if (0 <= port) and (port <= 7):
            # 受け取ったポート番号が、範囲を超えてないこと
            if arg_val == 1:
                # 指定の番号をON
                val = 0x01 << port
                # 現在のON場所を読み込み
                current = self.bus.read_byte_data(self.__ICADDR, REG_GPIOA)
                # 制御する箇所をORして作る
                control = current | val
            else:
                # 指定の番号をOFF
                val = 0x01 << port
                # 現在のON場所を読み込み
                current = self.bus.read_byte_data(self.__ICADDR, REG_GPIOA)
                # 制御する箇所をANDして作る
                control = current & ~val
            # ON場所を更新
            self.bus.write_byte_data(self.__ICADDR, REG_OLATA, control)
        elif port == 9:
            # ポート*9番を指定されたときは、全ポートを同時操作
            if arg_val == 1:
                # 全てON
                self.bus.write_byte_data(self.__ICADDR, REG_OLATA, 0xff)
            else:
                # 全てOFF
                self.bus.write_byte_data(self.__ICADDR, REG_OLATA, 0x00)
        else:
            # それ以外の時はエラー
            print("Ch %s is not found." % (arg_ch))

    def Read(self):
        """
        GPIO入力状態の更新
        Parameters
        ----------
        arg_ch : 
            ch番号
            (出力ピン番号のリストで指定した順番。0から始まる値で指定)
        """
        # GPIO読み込み
        i2c_in_val = self.bus.read_byte_data(self.__ICADDR, REG_GPIOB)

        # 指定のポートだけ読み込み
        # 現在のH/L状態の一時格納
        port_now = []
        val_now = []
        for ch in range(8):
            # ON状態のチェック
            if (i2c_in_val >> ch) & 0x01 == 1:
                val = 1
            else:
                val = 0
            # 現在のH/L状態に追記
            port_now.append(ch)
            val_now.append(val)
        # ログの表示
        # print("Port (IN): %s -> %s (INTCAP) %s " %
        #        (port_now, val_now, bin(i2c_in_val)))
        # 読んだ値を返す
        return val_now
