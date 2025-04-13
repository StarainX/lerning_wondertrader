# 日线其实没啥用，这里只是为了完善tick中的pre_close、pre_settle、pre_interest数据
# 本篇的目的其实是因为从tick到dsb的转换过程中需要在当提tick数据中填写昨日持仓、成交额和成交量。
# 挺简单，只有一点需要注意，就是请求间隔，免得被封禁。
import os
import akshare as ak

#日线数据的存储路径
path='D:\WorkingFiels\wtstudio\data\his\day\CZCE'
#需要拉取合约的CSV目录
root_dir='D:\软件下载目录\百度云\期货test'


# 遍历目录中的文件夹获得所有文件名，去除路径数据，去除文件名中的.csv扩展名
def collect_and_clean_filenames(root_dir):
    # 获取所有直接子文件夹的路径
    subdirs = [os.path.join(root_dir, d) for d in os.listdir(root_dir)
               if os.path.isdir(os.path.join(root_dir, d))]

    file_names = []
    for subdir in subdirs:
        # 遍历子文件夹中的所有条目
        for entry in os.listdir(subdir):
            entry_path = os.path.join(subdir, entry)
            # 确保是文件而非文件夹
            if os.path.isfile(entry_path):
                file_names.append(entry)

    # 去重并保留顺序（Python3.7+字典有序）
    seen = set()
    unique_files = [f for f in file_names if not (f in seen or seen.add(f))]

    # 移除.csv后缀（精确处理扩展名）
    cleaned_files = [os.path.splitext(f)[0] for f in unique_files]

    return cleaned_files


result = collect_and_clean_filenames(root_dir)
# 处理列表中的合约名，给所有合约数字前加上2，因为新浪接口合约数字部分是2开头的四位合约
result = [s[:2] + '2' + s[2:] for s in result]

print(result)
i=0
for each in result:
        futures_zh_daily_sina_df = ak.futures_zh_daily_sina(symbol=each)
        print(futures_zh_daily_sina_df)
        break



