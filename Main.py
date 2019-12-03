#!/usr/bin/env /usr/bin/python3
# -*- coding: utf-8 -*-
# -----------------------------------------------
# POKAYOKE System (Python Edition)
#
# The MIT License (MIT)
# Copyright (C) 2019 myasu.
# -----------------------------------------------

import time
import GpioOut


def test_out():
    """
    GPIOランプ点灯テスト
    """
    port = [26, 19, 13, 6]
    out = GpioOut.GpioOut(port)
    # 点灯
    print("-- LAMP TEST --")
    for mode in [1, 2, 3, 4, 0]:
        print(" > MODE %d" % (mode))
        for ch in range(len(port)):
            out.Update(ch, mode)
        time.sleep(3.0)


def main(args=None):
    """
    メイン関数
    Parameters
    ----------
    """
    try:
        test_out()
    except KeyboardInterrupt:
        pass
    finally:
        pass


if __name__ == '__main__':
    main()
