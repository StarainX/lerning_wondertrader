#  这是一个将csv格式tick数据转换为自定义的dsb压缩格式的脚步。
#  tick数据量大，转换生成比较耗时，所以会先判断原位置有没有文件，有则会跳过，避免重复转换。

from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSTickStruct
import pandas as pd
import os
import re


# 需要提前设置好交易码代码
exchg_name = 'CZCE'
# 需要提取的文件路径
root_directory = 'D:\\软件下载目录\\百度云\\期货test'  # 替换为实际路径
# 需要转存到的路径根目录
save_directory = 'D:\\WorkingFiels\\wtstudio\\data\\his\\tick\\CZCE'

# 目录不存在则抛出提示退出
if not os.path.exists(root_directory):
    print(f"⚠ 输入路径不存在，请检查路径是否正确！")
    exit(1)
if not os.path.exists(save_directory):
    print(f"⚠ 输入路径不存在，请检查路径是否正确！")
    exit(1)


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


csv_list = collect_csv_paths(root_directory)


# 打印处理前的信息
print(f"压缩档案内总共需要转换的文件数例: {len(csv_list)}")
if len(csv_list) > 0:
    print(f"开始文件: {csv_list[0]}")
    print(f"结束文件: {csv_list[-1]}")

# 使用列表推导式过滤需要保留的条目
# 这里原先在遍历时候直接从原列表remove，导致索引错位。正常做法是构建新列表，不能直接在循环中对原列表进行修改。
filtered_list = []
for each in csv_list:
    # 使用 os.path 处理路径
    dir_path = os.path.dirname(each)
    file_name = os.path.basename(each)
    base_name = os.path.splitext(file_name)[0]  # 安全去除扩展名

    # 获取路径最后组成部分
    path_elements = split_file_path(dir_path)
    dir_last_part = path_elements[-1] if path_elements else ''

    # 分割文件名中的字母和数字
    name_part, num_part = split_alpha_numeric(base_name)
    if not name_part:
        name_part = "unknown"
    if not num_part:
        num_part = "000"

    # 构建新路径
    new_dir = os.path.join(save_directory, dir_last_part)
    new_filename = f"{exchg_name}.{name_part}.{num_part}_tick_{dir_last_part}.dsb"
    new_filepath = os.path.join(new_dir, new_filename)

    # 仅保留没有生成最终文件的条目
    if not os.path.exists(new_filepath):
        filtered_list.append(each)

csv_list = filtered_list

# 打印处理后的信息
print(f"剔除已存在文件后需要转换的文件数量: {len(csv_list)}")
if len(csv_list) > 0:
    print(f"开始文件: {csv_list[0]}")
    print(f"结束文件: {csv_list[-1]}")
print(csv_list)

# 从csv_list中取出文件名，并删除其中的.csv后缀,实际上生成所有合约名。
csv_name = [
    os.path.splitext(os.path.basename(file_path))[0]
    for file_path in csv_list]

#breakpoint()
dtHelper = WtDataHelper()

s = 0
for each in csv_list:
    with open(each) as f:
        encode = f.encoding

    df = pd.read_csv(each, encoding=encode)

    # 这里有个小坑，9.0版本以后vol会被写入为0，0，把WTSBarStruct中的volume改为vol即可，应该是版本迭代留下的坑，数据实际最终还是写入到volume字段。
    # 先重命名所有可用的现存列
    df = df.rename(columns={
        # 'InstrumentID': 'code',  # 合约代码
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

    # 这三个字段看看能不能从akshare日k上拉一下。不过就算只拿单个合约的日线，合约还是很多，一次查询太多会被封号。
    # 解决方法是获取上一个交易日文件夹内同名合约的最后一条数据中的收盘和持仓
    # "pre_close",
    # "pre_settle",
    # "pre_interest",


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
    name, number = split_alpha_numeric(csv_name[s])

    newfilename = save_directory + '\\' + file_path_elements[
        -1] + '\\' + exchg_name + '.' + name + '.' + number + '_tick_' + file_path_elements[-1] + '.dsb'

    # df.to_csv(newfilename+'.csv',index=False)

    # 判断目录是否存在，不存在则创建
    write_dir = save_directory + '\\' + file_path_elements[-1]
    if not os.path.exists(write_dir):
        # 如果目录不存在，则创建目录
        os.makedirs(write_dir)
        print(f"目录 {write_dir}不存在，已创建")

    # 判断newfilename是否存在，存在则跳过，不存在则调用dtHelper.store_ticks写入
    if not os.path.exists(newfilename):
        # 调用store_ticks方法转换成dsb格式文件，注意目录存在才会写入，且不能有中文名，不会报错。
        dtHelper.store_ticks(tickFile=newfilename, firstTick=buffer, count=len(df))
        print(newfilename + '转换完毕')
    else:
        print(f"{newfilename}已存在，跳过。")

    s += 1
    # if s == 1:
    #     break
