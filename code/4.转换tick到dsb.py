from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSTickStruct
import pandas as pd
import os
import re

# 需要提前设置好交易码代码
exchg_name = 'CZCE'

# 需要提取的文件路径
root_directory = 'D:\\软件下载目录\\百度云\\test'  # 替换为实际路径

#需要转存到的路径根目录
save_directory = 'D:\\WorkingFiels\\wtstudio\\data\\his\\tick\\CZCE'


def collect_csv_paths(root_dir):
    csv_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                full_path = os.path.join(root, file)
                csv_files.append(full_path)
    return csv_files


# 一个路径分割方法方便后面合成文件名
def split_file_path(path):
    # 将路径中的反斜杠统一替换为斜杠
    normalized_path = path.replace('\\', '/')
    # 使用斜杠进行分割
    parts = normalized_path.split('/')
    # 过滤空字符串
    return [part for part in parts if part]


# 一将FG303这种'字母+数字'形式合约名称分割为字母和数字两部分。
def split_alpha_numeric(s):
    match = re.match(r"([A-Za-z]+)(\d+)", s)
    if match:
        alpha_part = match.group(1)
        numeric_part = match.group(2)
        return alpha_part, numeric_part
    else:
        return None, None


# 示例用法
# file_path = "/home/user/documents/file.txt"
# result = split_file_path(file_path)
# print(result)  # 输出：['', 'home', 'user', 'documents', 'file.txt']
#
# windows_path = "C:\\Program Files\\Python\\python.exe"
# result = split_file_path(windows_path)
# print(result)  # 输出：['C:', 'Program Files', 'Python', 'python.exe']
#
# mixed_path = "mixed\\separators//and/slashes"
# result = split_file_path(mixed_path)
# print(result)  # 输出：['mixed', 'separators', '', 'and', 'slashes']


# 取出文件路径方便后面使用
csv_list = collect_csv_paths(root_directory)

# 取出文件名方便后面使用
csv_name = [
    os.path.splitext(os.path.basename(file_path))[0]
    for file_path in csv_list]

# print(len(csv_list), len(csv_name))

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
    # 不知道为啥这里要二进制形式的
    df['exchg'] = b'CZCE'  # 交易所代码
    df['code'] = csv_name[s].encode('utf-8')

    # 去掉开盘前的空值

    # 使用diff()有个问题，就是第一个值是NaN不会被赋值。
    # 其实集合竞价也有成交量、成交额、仓差的变化，不过会在开盘前一分钟统一绘制。开盘时开始计算差额。
    # 计算每tick成交量
    df['volume'] = df['total_volume'].diff()
    # 计算每tick成交额
    df['turn_over'] = df['total_turnover'].diff()
    # 计算仓差，
    df['diff_interest'] = df['open_interest'].diff()

    # 计算开盘价
    # 第1个元素f['price'][0]是开机时间只有持仓时间没有其他
    # 且非主力合约存在前10毫秒没报价的问题。所以open需要寻找price里第一个非零值。
    df['open'] = df['price'][df['price'].ne(0).idxmax()]
    df['high'] = df['price'].max()  # 最高价
    df['low'] = df['price'].min()  # 最低价
    # df['settle_price'] = df['settle_price']# 不知道结算价怎么算的，不搞了。
    df['action_date'] = df['trading_date']

    # 将UpdateTime列转换为时间戳格式
    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'], format='%H:%M:%S')
    # 提取小时、分钟、秒并转换为整数
    # 这里虽然加上了UpdateMillisec，实际上源数据库都是0……
    df['action_time'] = (df['UpdateTime'].dt.hour * 10000 + df['UpdateTime'].dt.minute * 100 + df[
        'UpdateTime'].dt.second) * 1000 + df['UpdateMillisec']

    # print(df['action_time'])

    df = df[
        ['exchg', 'code', 'price', 'open', 'high', 'low', 'total_volume', 'total_volume', 'volume', 'total_turnover',
         'turn_over', 'open_interest', 'diff_interest', 'trading_date', 'action_date', 'action_time', 'bid_price_0',
         'bid_qty_0',
         'ask_price_0', 'ask_qty_0']]

    BUFFER = WTSTickStruct * len(df)
    buffer = BUFFER()


    def assign(procession, buffer):
        tuple(map(lambda x: setattr(buffer[x[0]], procession.name, x[1]), enumerate(procession)))


    df.apply(assign, buffer=buffer)
    # print(df)
    # print(buffer[s].to_dict())

    # df.to_csv(newfilename+'.csv',index=False)

    # 整理重命名规则，类似CFFEX.IF.HOT_tick_20210104
    file_path = os.path.dirname(csv_list[s])
    file_path_elements = split_file_path(file_path)
    name,number= split_alpha_numeric(csv_name[s])

    newfilename = save_directory + '\\'+file_path_elements[-1]+'\\' + exchg_name + '.' +name+'.'+number+ '_tick_' + file_path_elements[-1] + '.dsb'

    #df.to_csv(newfilename+'.csv',index=False)


    #判断目录是否存在，不存在则创建
    write_dir = save_directory + '\\'+file_path_elements[-1]
    if not os.path.exists(write_dir):
        # 如果目录不存在，则创建目录
        os.makedirs(write_dir)
        print(f"目录 {write_dir}不存在，已创建")


    #调用store_ticks方法转换成dsb格式文件，注意目录存在才会写入，且不能有中文名，不会报错。
    dtHelper.store_ticks(tickFile=newfilename, firstTick=buffer, count=len(df))

    s += 1
    print(newfilename+'转换完毕')
    # if s == 1:
    #     break
