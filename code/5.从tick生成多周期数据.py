##  解决日线数据和分钟数据的重采样问题。
##  只需要生成min1和min5周期，其它周期5倍数通过min5合成，非五倍数周雅在个人认知中没什么价值。
from pathlib import Path, PurePath
import os
import re
from wtpy.wrapper import WtDataHelper
from wtpy import WtDtServo
import pandas as pd

#  第一步是遍历所有文件夹……又是遍历，感觉磁盘迟早被我搞穿的样子。
root_dir = 'D:/WorkingFiels/wtstudio/data/his/ticks'

dt_helper = WtDataHelper()  # 这个是wtpy的类，用来读取、存储和重采样数据。
# 初始化WtDtServo
dtServo = WtDtServo()
dtServo.setBasefiles(folder="D:/WorkingFiels/pythonProject/WonderTrader/wtpy-dev/demos/common/")
dtServo.setStorage(path="D:\\WorkingFiels\\wtstudio\\data")


def get_all_files(root_dir):
    """遍历指定目录下的所有文件，返回路径列表（字符串形式）"""
    root = Path(root_dir)
    return [str(file) for file in root.rglob("*") if file.is_file()]


# 示例用法
file_list = get_all_files(root_dir)
print(file_list)


#  本来想加入判断逻辑呢，如果目标文件（已经转换的）存在就跳过，但是这种方法需要区分当期合约和历史已经下架的合约，已经下架的合约不用更新。
#  这样有点麻烦，先走批量转换的路子，后面有机会了再慢慢修改吧。总之要写好用的代码就是很麻烦的……

## 看了下m5的文件，里面的字段在现有tick数据中都有，所以应该还是很好搞的。

# 从获取tick和重采样的函数来看，列表中的合约名、日期、交易所这三个字段得拆分出来。
# 这几个数据额还是好定位的，分别是倒数第一、第二、第三个路径字符串切片，
# 有点蛋疼的是没发现有从tick重采样到分钟、day级别的函数！只有从1分钟级别往上采样的。好吧自己写了。
def extract_contract_info(file_path):
    """保留路径的文件名为contract_name、倒数第一级目录名为contract_date、倒数第二级目录名为contact_exchg"""
    path = PurePath(file_path)
    parts = path.parts

    if len(parts) < 3:
        raise ValueError("文件路径至少需要包含三级目录和一个文件名")

    filename = parts[-1]
    name, ext = os.path.splitext(filename)
    contract_name = name if ext.lower() == '.dsb' else filename

    return {
        "contract_name": contract_name,
        "contract_date": parts[-2],
        "contact_exchg": parts[-3]
    }


def resample_ticks_to_min1(tick_df):
    """从tick重采样到min1"""
    df = tick_df

    print(df)

    breakpoint()
    df['exchg'] = df['exchg'].str.decode('utf-8').str.strip("'")
    df['code'] = df['code'].str.decode('utf-8').str.strip("'")

    # 时间解析函数（修复版）
    def parse_time(row):
        # 将action_time转换为字符串并补足8位
        time_str = f"{row['action_time']:08d}"
        # 正确截取时间分量
        try:
            # 分解为小时、分钟、秒
            hh = int(time_str[:2])
            mm = int(time_str[2:4])
            ss = int(time_str[4:6])
            # 自动处理非法时间（如92小时）
            if hh >= 24:
                hh = hh % 24
                new_date = pd.to_datetime(row['action_date'], format='%Y%m%d') + pd.DateOffset(days=1)
                date_str = new_date.strftime('%Y%m%d')
            else:
                date_str = str(row['action_date'])
            return pd.to_datetime(f"{date_str}{hh:02d}{mm:02d}{ss:02d}", format='%Y%m%d%H%M%S')
        except:
            return pd.NaT

    # 应用时间解析
    df['datetime'] = df.apply(parse_time, axis=1)
    df = df.dropna(subset=['datetime']).sort_values('datetime').set_index('datetime')

    # 前向填充持仓量
    df['open_interest'] = df.groupby(['exchg', 'code'])['open_interest'].ffill()

    # 聚合规则
    agg_rules = {
        'price': ['first', 'max', 'min', 'last'],
        'volume': 'sum',
        'turn_over': 'sum',
        'open_interest': 'last',
    }

    # 分组重采样
    resampled = (
        df
        .groupby(['exchg', 'code'])
        .resample('1min')
        .agg(agg_rules)
        .reset_index()
    )

    # 处理列名
    resampled.columns = [
        'exchg', 'code', 'datetime',
        'open', 'high', 'low', 'close',
        'volume', 'turnover', 'open_interest'
    ]

    # 计算结算价
    resampled['settle'] = resampled['turnover'] / resampled['volume'].replace(0, pd.NA)

    # 计算仓差
    resampled['diff'] = resampled.groupby(['exchg', 'code'])['open_interest'].diff()

    # 生成时间字段
    resampled['date'] = resampled['datetime'].dt.strftime('%Y%m%d')
    resampled['bartime'] = resampled['datetime'].dt.strftime('%Y%m%d%H%M')

    # 处理无效值
    fill_cols = ['open', 'high', 'low', 'close', 'settle']
    resampled[fill_cols] = resampled.groupby(['exchg', 'code'])[fill_cols].ffill().infer_objects(copy=False)

    # 字段排序
    column_order = [
        'date', 'exchg', 'code', 'open', 'high', 'low', 'close',
        'settle', 'turnover', 'volume', 'open_interest', 'diff', 'bartime'
    ]
    return resampled[column_order].fillna(0).infer_objects(copy=False)

def save_ticks_to_min1(tick_df):
    df= tick_df

    dt_helper.s


i = 0
for each in file_list:
    """提取列表中每个路径的交易所名、日期、合约名"""
    info = extract_contract_info(file_list[i])
    print(info['contract_name'], info['contract_date'], info['contact_exchg'])

    # 自己线写个从tick采样到min1的方法，这个wtpy里没有。

    stdCode = info['contact_exchg'] + '.' + re.sub(r'\d', '', info['contract_name']) + '.' + info['contract_name']
    iDate = int(info['contract_date'])
    print(stdCode + ',' + str(iDate))

    if dtServo.local_api is None:
        print("dtServo.local_api 未正确初始化")
        break
    data_old = dtServo.get_ticks_by_date(stdCode, iDate).to_df()

    data_old.to_csv(stdCode + '_' + str(iDate) + '.csv')


    data_new = resample_ticks_to_min1(data_old)

    print(data_new)


    break

# data = dtServo.get_ticks_by_date("CZCE.FG.FG505", 202501260930).to_df()
