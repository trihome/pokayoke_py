#!/bin/bash
#--------------------------------------------------------------------
#バックグラウンド実行用のスクリプト
#--------------------------------------------------------------------

#変数の設定
SCRIPTDIR=/home/pi/gitwork/python/poka
LOGDIR=$SCRIPTDIR/log

#実行
exec /usr/bin/env /usr/bin/python3 $SCRIPTDIR/Main.py -v >> $LOGDIR/run.log 2>&1
