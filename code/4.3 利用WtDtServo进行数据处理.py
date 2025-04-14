from wtpy import WtDtServo

dtServo = WtDtServo()
# 完成初始化才能开始调用数据
dtServo.setBasefiles(folder="D:/WorkingFiels/pythonProject/WonderTrader/wtpy-dev/demos/common/")
#dtServo.setStorage("../../wtpy-dev/demos/storage/")
dtServo.setStorage(path="D:\\WorkingFiels\\wtstudio\\data")


#正确写法，注意主力和非主力的stdCode格式不一样,主力只需要些HOT,分月合约需要写FG505这种。
data = dtServo.get_ticks("CZCE.FG.FG505", 202501260930).to_df()
#data = dtServo.get_bars("CFFEX.IF.HOT", "min5", fromTime=202205010930, endTime=202205281500)
#data =dtServo.get_bars_by_date("CFFEX.FG.FG505", "min5", 202205010930)
print(len(data))
