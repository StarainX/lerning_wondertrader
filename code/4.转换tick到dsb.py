from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSTickStruct
import pandas as pd
import os
import re


def collect_csv_paths(root_dir):
    csv_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                full_path = os.path.join(root, file)
                csv_files.append(full_path)
    return csv_files


# 需要提取的文件路径
root_directory = 'D:\\软件下载目录\\百度云\\test'  # 替换为实际路径
#取出文件路径方便后面使用
csv_list = collect_csv_paths(root_directory)

#取出文件名方便后面使用
csv_name = [
    os.path.splitext(os.path.basename(file_path))[0]
    for file_path in csv_list]

#print(len(csv_list), len(csv_name))

dtHelper = WtDataHelper()
s = 0
for each in csv_list:
    with open(each) as f:
        encode = f.encoding

    df = pd.read_csv(each, encoding=encode)

    # 这里有个小坑，9.0版本以后vol会被写入为0，0，把WTSBarStruct中的volume改为vol即可，应该是版本迭代留下的坑，数据实际最终还是写入到volume字段。
    # 先重命名所有可用的现存列
    df = df.rename(columns={
        'InstrumentID': 'code',  # 合约代码
        'TradingDay': 'trading_date',
        'LastPrice': 'price',  # 最新价
        'Volume': 'total_volume',  # 总成交量
        'BidPrice1': 'bid_price_0',  # 申买价1
        'BidVolume1': 'bid_qty_0',  # 申买量1
        'AskPrice1': 'ask_price_0',  # 申卖价1
        'AskVolume1': 'ask_qty_0',  # 申卖量1
        'Turnover': 'total_turnover',  # 总成交额
        'OpenInterest': 'open_interest',  # 持仓量
    })

    # 增加几列需要运算得出的字段
    df['exchg'] = "b'CZCE'" # 交易所代码
    df['code'] = 'b' + "'"+csv_name[s]+"'"

    print(df['exchg'])


    #使用diff()有个问题，就是第一个值是NaN不会被赋值。实际上这个值应该是和上个交易日的最后一个tick的值结合进行计算，这里先赋值为0
    # 计算每tick成交量
    df['volume'] = df['total_volume'].diff()
    # 计算每tick成交额
    df['turn_over'] = df['total_turnover'].diff()
    # 计算仓差
    df['diff_interest'] = df['open_interest'].diff()
    print(df['diff_interest'])
    breakpoint()

    # 计算开盘价
    # 第1个元素f['price'][0]是开机时间只有持仓时间没有其他
    # 且非主力合约存在前10毫秒没报价的问题。所以open需要寻找price里第一个非零值。
    df['open'] = df['price'][df['price'].ne(0).idxmax()]
    df['high'] = df['price'].max()  # 最高价
    df['low'] = df['price'].min()  # 最低价
    # df['settle_price'] = df['settle_price']# 不知道结算价怎么算的，不搞了。
    df['action_date'] = df['trading_date']



    #df['action_time'] = int(df['UpdateTime'].replace(":",""))*1000+int(df['UpdateMillisec']) # 正常需要加上毫秒，但数据里毫秒都是0，所以懒得加了。
    # 将UpdateTime列转换为时间戳格式
    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'], format='%H:%M:%S')
    # 提取小时、分钟、秒并转换为整数
    #这里虽然加上了UpdateMillisec，实际上源数据库都是0……
    df['action_time'] = (df['UpdateTime'].dt.hour * 10000 + df['UpdateTime'].dt.minute * 100 + df['UpdateTime'].dt.second)*1000+df['UpdateMillisec']

    #print(df['action_time'])

    # 计其实还需要计算净持仓，但是这个需要昨日昨日持仓，先不弄，最后写入数据dsb后再统一批处理。

    df = df[
        ['exchg', 'code', 'price', 'open', 'high', 'low', 'total_volume', 'total_volume', 'volume', 'total_turnover',
         'turn_over', 'open_interest', 'diff_interest','trading_date', 'action_date', 'action_time', 'bid_price_0', 'bid_qty_0',
         'ask_price_0', 'ask_qty_0']]


    BUFFER = WTSTickStruct * len(df)
    buffer = BUFFER()


    def assign(procession, buffer):
        tuple(map(lambda x: setattr(buffer[x[0]], procession.name, x[1]), enumerate(procession)))


    df.apply(assign, buffer=buffer)
    # print(df)
    # print(buffer[s].to_dict())

    newfilename = './data/' + each + '.dsb'
    #print(newfilename)

    # df.to_csv(newfilename+'.csv')

    # 这里有坑，目录存在才会写入，且不能有中文名，不会报错。
    exchg = 'SHFE'

    dtHelper.store_bars(barFile=newfilename, firstBar=buffer, count=len(df), period="m1")

    s += 1
    # print(df)
    if s == 1:
        break
