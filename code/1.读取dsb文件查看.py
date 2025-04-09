from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSBarStruct, WTSTickStruct
from ctypes import POINTER
from wtpy.SessionMgr import SessionMgr
import pandas as pd

dataReader = WtDataHelper()

testdata = dataReader.read_dsb_ticks("D:\\WorkingFiels\\pythonProject\\WonderTrader\\wtpy-dev\\demos\\storage\\bin\\ticks\\CFFEX.IF.HOT_tick_20210104.dsb")

# 这里不能直接print,因为WtDataHelper()读取的是一个封装的WtNpTicks对象，直接print的是其内存地址。我们需要调用WtNpTicks的内置方法来读取数据本体。
# 可以通过.__data__ 或者.ndarray进行调用
print(testdata.__data__, '\n伟大的分隔符')
#print(testdata.ndarray)

#不太了解每一列的意义，我们转换成csv格式查看。
dataReader.dump_ticks("D:\\WorkingFiels\\pythonProject\\WonderTrader\\wtpy-dev\\demos\\storage\\bin\\ticks\\CFFEX.IF.HOT_tick_20210104.csv", testdata)
