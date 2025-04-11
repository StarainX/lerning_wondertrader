## 主要目的是将自己这边主力合约的格式转换成wondertrader的格式进行转换，有一说一吧，我挺讨厌它的格式的其实，和其它应用格式差异太大了，它的数据只能自己用，别的要用还得剔除多余字符串转一遍。除非是一直准备

## 写完看看能不能搞个GUI界面。

## wondertrader分钟格式的命名规则为：交易所代码.品种代码_HOT.dsb，如CFFEX.IF_HOT.dsb

# 品种和合约信息可以从commodities.json和contracts.json拉取。


#
from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSBarStruct, WTSTickStruct
import pandas as pd
import os
import re

# 这是从commodities.json中提取处理过的wondertrader的品种名称
json_data = {'CFFEX': {'IC', 'IF', 'IH', 'IM', 'T', 'TF', 'TL', 'TS','LC','SI'},
             'CZCE': {'AP', 'CF', 'CJ', 'CY', 'FG', 'JR', 'LR', 'MA', 'OI', 'PF', 'PK', 'PM', 'PX', 'RI', 'RM', 'RS',
                      'SA', 'SF', 'SH', 'SM', 'SR', 'TA', 'UR', 'WH', 'WT','ZC'},
             'DCE': {'a', 'b', 'bb', 'c', 'cs', 'eb', 'eg', 'fb', 'i', 'j', 'jd', 'jm', 'l', 'lh', 'm', 'p', 'pg', 'pp',
                     'rr', 'v', 'y'}, 'GFEX': {'lc', 'si'}, 'INE': {'bc', 'ec', 'lu', 'nr', 'sc'},
             'SHFE': {'ag', 'al', 'ao', 'au', 'br', 'bu', 'cu', 'fu', 'hc', 'ni', 'pb', 'rb', 'ru', 'sn', 'sp', 'ss',
                      'wr', 'zn'}}

# 需要转换的数据的目录
path = 'D:\资料\交易盘口数据\中国所有期货主力合约1分钟K线历史数据（2005年-2024年7月25日）'

file_list_old = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

print(file_list_old)

# 这里是对原有数据的文件名处理，主要是把合约代码和文件名更改为wondertrader的格式，以便最后for循环批量生成。

# 将file_list中所有元素的9999改为.HOT
file_list_new = [file.replace('9999', '.HOT') for file in file_list_old]
# 删除所有元素第二个.和第三个.之间的字母
file_list_new = [re.sub(r'(\.[^.]+)\.[^.]+(\.[^.]+)', r'\1\2', file) for file in file_list_new]
# 修改csv扩展名
file_list_new = [file.replace('csv', 'dsb') for file in file_list_new]
# 由于自己的数据文件名大小写与wondertrader的不一致，需要修一下。思路是从commodities.json中寻找对应。
commodities_oldname = [file.replace('.HOT.dsb', '') for file in file_list_new]

commodities_ONLYnames = [os.path.basename(name) for name in commodities_oldname]

# 构建映射字典：键为大写形式，值为原始正确形式
symbol_mapping = {}

for exchange, symbols in json_data.items():
    for symbol in symbols:
        symbol_upper = symbol.upper()
        symbol_mapping[symbol_upper] = (exchange, symbol)

# 处理原始列表，调整大小写不一致的项
adjusted_list = []
for s in commodities_ONLYnames:
    key = s.upper()
    if key in symbol_mapping:
        exchange, correct_symbol = symbol_mapping[key]
        adjusted_list.append(f"{exchange}.{correct_symbol}")
    else:
        adjusted_list.append(s)

print(adjusted_list)

dtHelper = WtDataHelper()
s = 0
for each in file_list_old:
    with open(each) as f:
        encode = f.encoding

    df = pd.read_csv(each, encoding=encode)
    # df = df.head(1000)
    df['date'] = pd.to_datetime(df['date'])
    df['date_only'] = df['date'].dt.date
    df['time_only'] = df['date'].dt.time
    df = df.drop(columns=['date'])
    df = df.drop(columns=['symbol'])


    #这里有个小坑，9.0版本以后vol会被写入为0，0，把WTSBarStruct中的volume改为vol即可，应该是版本迭代留下的坑，数据实际最终还是写入到volume字段。
    df = df.rename(columns={
        'date_only': 'date',
        'time_only': 'time',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'volume': 'vol',
        'money': 'turnover',
        'open_interest': 'open_interest',
    })
    df['date'] = df['date'].astype('datetime64[ns]').dt.strftime('%Y%m%d').astype('int64')
    df['time'] = df['time'].astype(str)



    #print(df['time'])
    df['time'] = (df['date']-19900000)*10000 + df['time'].str.replace(':', '').str[:-2].astype('int')
    df = df[['date', 'time', 'open', 'high', 'low', 'close', 'vol', 'turnover', 'open_interest']]

    BUFFER = WTSBarStruct * len(df)
    buffer = BUFFER()

    def assign(procession, buffer):
        tuple(map(lambda x: setattr(buffer[x[0]], procession.name, x[1]), enumerate(procession)))




    df.apply(assign, buffer=buffer)
    #print(df)
    print(buffer[s].to_dict())




    newfilename='data/'+adjusted_list[s]+'_HOT.dsb'

    #df.to_csv(newfilename+'.csv')

    # 这里有坑，目录存在才会写入，且不能有中文名，不会报错。
    dtHelper.store_bars(barFile=newfilename, firstBar=buffer, count=len(df), period="m1")

    s += 1
    #print(df)
    # if s == 1:
    #     break
