#
from concurrent.futures import ProcessPoolExecutor
from wtpy.wrapper import WtDataHelper
from wtpy.WtCoreDefs import WTSTickStruct
from dataclasses import dataclass
from tqdm import tqdm
import quantlib as ql
import pandas as pd
import os
import re
import logging


# 配置日志记录
logging.basicConfig(
    filename='conversion.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


@dataclass
class PathConfig:
    exchg_name: str = 'CZCE'
    root_dir: str = 'D:\\软件下载目录\\百度云\\sa'
    save_root: str = 'D:\\WorkingFiels\\wtstudio\\data\\his\\ticks'

    @property
    def save_dir(self):
        return os.path.join(self.save_root, self.exchg_name)


cfg = PathConfig()

# # 初始化显示配置
# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', None)


def validate_paths():
    """路径验证"""
    if not os.path.exists(cfg.root_dir):
        raise FileNotFoundError(f"输入路径不存在: {cfg.root_dir}")
    if not os.path.exists(cfg.save_dir):
        os.makedirs(cfg.save_dir, exist_ok=True)


def collect_csv_paths(root_dir: str) -> list:
    """收集CSV文件路径"""
    return [
        os.path.join(root, file)
        for root, _, files in os.walk(root_dir)
        for file in files
        if file.lower().endswith('.csv')
    ]

def collect_csv_dates(root_dir: str) -> list:
    """收集CSV文件路径"""
    return [
        os.path.join(root, file)
        for root, _, files in os.walk(root_dir)
        for file in files
        if file.lower().endswith('.csv')
    ]


def split_alpha_numeric(s: str) -> tuple:
    """分割字母数字组合"""
    match = re.match(r"([A-Za-z]+)(\d+)", s)
    return (match.groups() if match else ("unknown", "000"))


def build_output_path(input_path: str) -> str:
    """构建输出路径"""
    dir_part = os.path.basename(os.path.dirname(input_path))
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    name_part, num_part = split_alpha_numeric(base_name)
    return os.path.join(cfg.save_dir, dir_part, f"{name_part}{num_part}.dsb")


def precheck_files(csv_list: list) -> list:
    """预检查文件是否存在"""
    existing_files = {
        build_output_path(p)
        for p in csv_list
        if os.path.exists(build_output_path(p))
    }
    return [p for p in csv_list if build_output_path(p) not in existing_files]


def process_tick_data(df: pd.DataFrame, csv_name: str) -> pd.DataFrame:
    """处理Tick数据"""
    # 数据清洗
    df = ql.QuantBox.dayAndnight(df)
    df = ql.QuantBox.plus_ms(df)

    # 向前填充
    df['LastPrice'] = df['LastPrice'].bfill()
    df['AveragePrice'] = df['AveragePrice'].bfill()

    # 列重命名
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

    # 计算衍生字段
    df = df.assign(
        exchg=lambda x: b'CZCE',
        code=lambda x: csv_name.encode('utf-8'),
        volume=lambda x: x['total_volume'].diff(),
        turn_over=lambda x: x['total_turnover'].diff(),
        diff_interest=lambda x: x['open_interest'].diff(),
        open=lambda x: x['price'].iloc[x['price'].ne(0).idxmax()],
        high=lambda x: x['price'].max(),
        low=lambda x: x['price'].min()
    )

    # 时间处理
    df['UpdateTime'] = pd.to_datetime(df['UpdateTime'], format='%H:%M:%S')
    df['action_time'] = (
                                df['UpdateTime'].dt.hour * 10000 +
                                df['UpdateTime'].dt.minute * 100 +
                                df['UpdateTime'].dt.second
                        ) * 1000 + df['UpdateMillisec']

    # 新增action_date列
    df['action_date'] = df['trading_date'].copy()

    # 类型转换（修复后的）
    int_cols = ['action_date', 'action_time']
    df[int_cols] = df[int_cols].astype(int)

    # 类型转换
    int_cols = ['action_date', 'UpdateTime', 'action_time']
    df[int_cols] = df[int_cols].astype(int)

    return df[['exchg', 'code', 'price', 'open', 'high', 'low',
               'total_volume', 'volume', 'total_turnover', 'turn_over',
               'open_interest', 'diff_interest', 'trading_date',
               'action_date', 'action_time', 'bid_price_0', 'bid_qty_0',
               'ask_price_0', 'ask_qty_0']]


def process_file(file_path: str):
    """处理单个文件"""
    try:
        output_path = build_output_path(file_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if os.path.exists(output_path):
            logging.info(f"Skipped existing: {output_path}")
            return

        # 读取数据
        with open(file_path) as f:
            encoding = f.encoding
        df = pd.read_csv(file_path, encoding=encoding)

        # 数据处理
        csv_name = os.path.splitext(os.path.basename(file_path))[0]
        df = process_tick_data(df, csv_name)

        # 创建缓冲区
        buffer = (WTSTickStruct * len(df))()
        df.apply(lambda col: tuple(
            setattr(buffer[i], col.name, val)
            for i, val in enumerate(col)
        ))

        # 保存数据
        WtDataHelper().store_ticks(
            tickFile=output_path,
            firstTick=buffer,
            count=len(df)
        )
        logging.info(f"Converted: {output_path}")

    except Exception as e:
        logging.error(f"Failed {file_path}: {str(e)}")
        raise



def main():
    validate_paths()
    csv_files = collect_csv_paths(cfg.root_dir)
    csv_files = precheck_files(csv_files)

    print(f"待处理文件数量: {len(csv_files)}")
    if not csv_files:
        return

    # 修改为进程池
    with ProcessPoolExecutor(max_workers= os.cpu_count()-10) as executor:  # 自动设置核心数
        list(tqdm(
            executor.map(process_file, csv_files),
            total=len(csv_files),
            desc="Processing Files"
        ))


if __name__ == "__main__":
    main()