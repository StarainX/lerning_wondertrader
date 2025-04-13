from wtpy import WtDtServo

dtServo = WtDtServo()
# 完成初始化才能开始调用数据
dtServo.setBasefiles(folder="D:/WorkingFiels/pythonProject/WonderTrader/wtpy-dev/demos/common/")
#dtServo.setStorage("../../wtpy-dev/demos/storage/")
dtServo.setStorage(path="D:\\WorkingFiels\\wtstudio\\data")


#data = dtServo.get_ticks_by_date("CZCE.FG.FG505", 20250206)
data = dtServo.get_ticks("CZCE.FG.FG505", 202501260930).to_df()
#data = dtServo.get_bars("CFFEX.IF.HOT", "min5", fromTime=202205010930, endTime=202205281500)
#data =dtServo.get_bars_by_date("CFFEX.IF.HOT", "min5", 202205010930)
print(len(data))
