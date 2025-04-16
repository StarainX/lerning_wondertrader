import multiprocessing
from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSTickStruct
import quantlib as ql
import pandas as pd
import os
import re

# 需要转换的原文件路径
root_directory = 'D:\\软件下载目录\\百度云\\期货csv'  # 替换为实际路径
# 需要转存到的路径根目录
save_directory = 'C:\\ticks'

pd.set_option('display.max_rows', None)  # 显示所有行
pd.set_option('display.max_columns', None)  # 显示所有列
pd.set_option('display.width', None)  # 调整宽度以适应所有列

# 品种与交易所映射关系
EXCHANGE_MAP = {
    "CFFEX": ["IC", "IF", "IH", "IM", "T", "TF", "TL", "TS"],
    "CZCE": ["AP", "BR", "CF", "CJ", "CY", "FG", "JR", "LR", "MA", "OI", "PF", "PK", "PM", "PX", "RI", "RM", "RS", "SA",
             "SF", "SH", "SM", "SR", "TA", "UR", "WH", "ZC"],
    "DCE": ["a", "b", "bb", "c", "cs", "eb", "eg", "fb", "i", "j", "jd", "jm", "l", "lh", "m", "p", "pg", "pp", "rr",
            "v", "y"],
    "GFEX": ["lc", "si"],
    "INE": ["bc", "ec", "lu", "nr", "sc"],
    "SHFE": ["ag", "al", "ao", "au", "br", "bu", "cu", "fu", "hc", "ni", "pb", "rb", "ru", "sn", "sp", "ss", "wr", "zn"]
}

def find_exchange(contract: str) -> str or None:
    """根据合约代码查找所属交易所"""
    alpha_part = ''.join(filter(str.isalpha, contract))
    for exchg, codes in EXCHANGE_MAP.items():
        if alpha_part in codes:
            return exchg
    return None

def collect_csv_paths(root_dir):
    """收集所有CSV文件路径"""
    csv_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.csv'):
                full_path = os.path.join(root, file)
                csv_files.append(full_path)
    return csv_files

def split_file_path(path):
    """分割文件路径"""
    normalized_path = path.replace('\\', '/')
    parts = normalized_path.split('/')
    return [part for part in parts if part]

def split_alpha_numeric(s):
    """分割字母和数字部分"""
    match = re.match(r"([A-Za-z]+)(\d+)", s)
    if match:
        return match.group(1), match.group(2)
    else:
        return None, None

def process_csv_file(csv_file, save_directory, trading_days):
    """处理单个CSV文件"""
    with open(csv_file) as f:
        encode = f.encoding
    df = pd.read_csv(csv_file, encoding=encode)
    df = ql.QuantBox.dayAndnight(df)
    df['LastPrice'] = df['LastPrice'].bfill()
    df['AveragePrice'] = df['AveragePrice'].bfill()
    df = ql.QuantBox.plus_ms(df)

    df = df.rename(columns={
        'TradingDay': 'trading_date',
        'LastPrice': 'price',
        'Volume': 'total_volume',
        'BidPrice1': 'bid_price_0',
        'BidVolume1': 'bid_qty_0',
        'AskPrice1': 'ask_price_0',
        'AskVolume1': 'ask_qty_0',
        'Turnover': 'total_turnover',
        'OpenInterest': 'open_interest',
    })

    base_name = os.path.splitext(os.path.basename(csv_file))[0]
    exchg_name = find_exchange(base_name)
    if exchg_name is None:
        exchg_name = "unknownexchange"
        print('发现未知品种无法找到所属交易所：', base_name)
        return

    current_date = split_file_path(csv_file)[-2] if len(split_file_path(csv_file)) >= 2 else None
    current_contract = split_file_path(csv_file)[-1] if len(split_file_path(csv_file)) >= 1 else None

    if current_date in trading_days:
        index = trading_days.index(current_date)
        if index > 0:
            previous_date = trading_days[index - 1]
            df_yestraday = pd.read_csv(
                root_directory + '\\' + exchg_name + '\\' + current_date + '\\' + current_contract, encoding=encode)
            df['pre_close'] = df_yestraday.iloc[-1]['LastPrice']
            df['pre_interest'] = df_yestraday.iloc[-1]['OpenInterest']
        else:
            df['pre_close'] = df['pre_interest'] = 0

    df['exchg'] = bytes(f'{exchg_name}', encoding='utf-8')
    df['code'] = bytes(base_name.encode('utf-8'))
    df['volume'] = df['total_volume'].diff().fillna(0)
    df['turn_over'] = df['total_turnover'].diff().fillna(0)
    df.loc[df['turn_over'] < 0, 'turn_over'] = 0
    df['diff_interest'] = df['open_interest'].diff().fillna(0)
    df['open'] = df['price'][df['price'].ne(0).idxmax()]
    df['high'] = df['price'].max()
    df['low'] = df['price'].min()

    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'], format='%H:%M:%S')
    df['action_time'] = (df['UpdateTime'].dt.hour * 10000 + df['UpdateTime'].dt.minute * 100 + df['UpdateTime'].dt.second) * 1000 + df['UpdateMillisec']
    df['action_date'] = df['trading_date'].astype(int)
    df['UpdateTime'] = df['UpdateTime'].astype(int)
    df['action_time'] = df['action_time'].astype(int)

    df = df[['exchg', 'code', 'price', 'open', 'high', 'low', 'total_volume', 'total_volume', 'volume', 'total_turnover', 'turn_over', 'open_interest', 'diff_interest', 'trading_date', 'action_date', 'action_time', 'pre_close', 'pre_interest', 'bid_price_0', 'bid_qty_0', 'ask_price_0', 'ask_qty_0']]

    BUFFER = WTSTickStruct * len(df)
    buffer = BUFFER()
    df.apply(lambda x: tuple(map(lambda y: setattr(buffer[y[0]], x.name, y[1]), enumerate(x))))

    name, number = split_alpha_numeric(base_name)
    newfilename = os.path.join(save_directory, exchg_name, current_date, f"{name}{number}.dsb")
    write_dir = os.path.join(save_directory, exchg_name, current_date)
    if not os.path.exists(write_dir):
        os.makedirs(write_dir)
        print(f"目录 {write_dir}不存在，已创建")

    if not os.path.exists(newfilename):
        dtHelper = WtDataHelper()
        dtHelper.store_ticks(tickFile=newfilename, firstTick=buffer, count=len(df))
        print(newfilename + '转换完毕')
    else:
        print(f"{newfilename}已存在，跳过。")

def main():
    if not os.path.exists(root_directory):
        print(f"⚠ 输入路径不存在，请检查路径是否正确！")
        exit(1)
    if not os.path.exists(save_directory):
        print(f"⚠ 输出路径不存在，请检查路径是否正确！")
        exit(1)

    csv_list = collect_csv_paths(root_directory)
    trading_days = sorted({os.path.basename(os.path.dirname(p)) for p in csv_list})

    print(f"压缩档案内总共需要转换的文件数例: {len(csv_list)}")
    if len(csv_list) > 0:
        print(f"开始文件: {csv_list[0]}")
        print(f"结束文件: {csv_list[-1]}")

    filtered_list = []
    for each in csv_list:
        dir_path = os.path.dirname(each)
        file_name = os.path.basename(each)
        base_name = os.path.splitext(file_name)[0]
        path_elements = split_file_path(dir_path)
        dir_last_part = path_elements[-1] if path_elements else ''
        name_part, num_part = split_alpha_numeric(base_name)
        if not name_part:
            name_part = "unknown"
        if not num_part:
            num_part = "000"
        excha = find_exchange(base_name)
        if excha is None:
            excha = "unknownexchange"
            print('发现未知品种无法找到所属交易所：', base_name)
            breakpoint()
        new_dir = os.path.join(save_directory, excha, dir_last_part)
        new_filename = f"{name_part}{num_part}.dsb"
        new_filepath = os.path.join(new_dir, new_filename)
        if not os.path.exists(new_filepath):
            filtered_list.append(each)

    csv_list = filtered_list
    print(f"剔除已存在文件后需要转换的文件数量: {len(csv_list)}")
    if len(csv_list) > 0:
        print(f"开始文件: {csv_list[0]}")
        print(f"结束文件: {csv_list[-1]}")

    # 使用多进程处理CSV文件
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        pool.starmap(process_csv_file, [(csv_file, save_directory, trading_days) for csv_file in csv_list])

if __name__ == "__main__":
    main()
