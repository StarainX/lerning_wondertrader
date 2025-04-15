# 本来想直接寻找上一个tick的数据，发现这样因为tick数据很多，挨个遍历打开量太大了
# 所以看看能不能线生成日线数据，再从日线数据里获取，调用量能小一些。
from wtpy import WtDtServo
from wtpy.WtDataDefs import WtNpKline

dtServo = WtDtServo()
# 完成初始化才能开始调用数据
dtServo.setBasefiles(folder="D:/WorkingFiels/pythonProject/WonderTrader/wtpy-dev/demos/common/")
# dtServo.setStorage("../../wtpy-dev/demos/storage/")
dtServo.setStorage(path="D:\\WorkingFiels\\wtstudio\\data")

# 正确写法，注意主力和非主力的stdCode格式不一样,主力只需要些HOT,分月合约需要写FG505这种。
# data = dtServo.get_bars("CFFEX.IF.HOT", "min5", fromTime=202205010930, endTime=202205281500)
# data =dtServo.get_bars_by_date("CFFEX.FG.FG505", "min5", 202205010930)
#data = dtServo.get_ticks("CZCE.FG.FG505", 202501260930).to_df()
data = dtServo.get_ticks_by_date("CZCE.FG.FG505", 20250122).to_df()
data.to_csv('20250122_'"CZCE.FG.FG505_tick.csv")

#返回值为None会AttributeError: 'NoneType' object has no attribute 'to_df'



print(data)



