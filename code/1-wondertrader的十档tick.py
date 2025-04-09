from wtpy.wrapper import WtDataHelper
import pandas as pd

dataReader = WtDataHelper()

testtick = dataReader.read_dsb_ticks(
    "D:\\WorkingFiels\\pythonProject\\WonderTrader\\wtpy-dev\\demos\\storage\\bin\\ticks\\CFFEX.IF.HOT_tick_20210104.dsb")

# 这里不能直接print,因为WtDataHelper()读取的是一个封装的WtNpTicks对象，直接print的是其内存地址。我们需要调用WtNpTicks的内置方法来读取数据本体。
# 可以通过.__data__ 或者.ndarray进行调用
# print(testdata.__data__, '\n伟大的分隔符')
# print(testdata.ndarray)

# 不太了解每一列的含义，通过csv看看。
csvtick = testtick.to_df()
csvtick.to_csv("dsb_tick.csv")

# 通过对比可以得出基本结论，wondertrader底层实际上是以全十档委托的形式构建WtNpTicks来存储tick行情的，应该是为了兼容A股的十档行情。
# 这种处理方式的优势是提高了底层数据结构的兼容性。同时，根据内盘市场的不同，转换出来的excel数据会多占用0.5~1倍的存储空间。
# 外盘有些蛋疼的交易所还有二十档行情…………
# 由于不清楚具体的执行机制，暂不清楚这种方式对于回测和实盘中策略的执行效率是否有明显的影响,理论上来说多少会减慢一点策略效率。

# 再查看下其它周期的文件底层格式：


testday = dataReader.read_dsb_bars(
    "D:\\WorkingFiels\\pythonProject\\WonderTrader\\wtpy-dev\\demos\\storage\\his\\min5\\CFFEX\\CFFEX.IF_HOT.dsb")


csvday=testday.to_df()
csvday.to_csv("dsb_m5.csv")
