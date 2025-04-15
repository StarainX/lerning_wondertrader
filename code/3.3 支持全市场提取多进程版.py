# -*- coding: utf-8 -*-
import os
import re
import zipfile
import time
import multiprocessing
import ctypes
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from colorama import Fore, Style, init
from functools import partial
from itertools import islice

# 初始化颜色支持（Windows需要）
init(autoreset=True)

# 交易所合约映射表
EXCHANGE_CONTRACTS = {
    "CFFEX": ["IC", "IF", "IH", "IM", "T", "TF", "TL", "TS"],
    "CZCE": ["AP", "BR", "CF", "CJ", "CY", "FG", "JR", "LR", "MA", "OI", "PF", "PK", "PM", "PX", "RI", "RM", "RS", "SA",
             "SF", "SH", "SM", "SR", "TA", "UR", "WH", "ZC"],
    "DCE": ["a", "b", "bb", "c", "cs", "eb", "eg", "fb", "i", "j", "jd", "jm", "l", "lh", "m", "p", "pg", "pp", "rr",
            "v", "y"],
    "GFEX": ["lc", "si"],
    "INE": ["bc", "ec", "lu", "nr", "sc"],
    "SHFE": ["ag", "al", "ao", "au", "br", "bu", "cu", "fu", "hc", "ni", "pb", "rb", "ru", "sn", "sp", "ss", "wr", "zn"]
}


def print_banner():
    """打印艺术字横幅"""
    title = "★☆★ 楠哥哥的tick提取工具箱 ★☆★"
    author = "作者：Deepseek、吉哈德韦伯"
    print(Fore.CYAN + "\n" + "=" * 90)
    print(Fore.CYAN + f"{title:^90}")
    print(Fore.CYAN + "=" * 90)
    print(f"{author:>88}")
    print()


def process_single_zip_optimized(args, output_dir, exchange_map):
    """优化后的单个ZIP处理函数"""
    zip_path, date_str = args
    extracted_count = 0
    try:
        # 主动让出CPU时间片（Linux/Windows通用）
        try:
            libc = ctypes.CDLL("libc.so.6") if os.name == 'posix' else ctypes.CDLL("msvcrt.dll")
            libc.sched_yield()
        except:
            pass

        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 预加载所有文件名列表
            file_list = zf.namelist()

            # 快速筛选候选文件
            candidate_files = [
                f for f in file_list
                if re.match(r'^[A-Za-z]+\d+\.csv$', f, re.IGNORECASE)
            ]

            # 精细匹配交易所
            for csv_file in candidate_files:
                product_code = re.match(r'^([A-Za-z]+)\d+\.csv$', csv_file, re.IGNORECASE).group(1).upper()
                exchange = exchange_map.get(product_code)

                if exchange:
                    dest_dir = os.path.join(output_dir, exchange, date_str)
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, csv_file)

                    if not os.path.exists(dest_path):
                        # 使用缓冲优化写入
                        BUFFER_SIZE = 16 * 1024 * 1024  # 16MB
                        with zf.open(csv_file) as src, open(dest_path, 'wb') as dst:
                            while True:
                                data = src.read(BUFFER_SIZE)
                                if not data:
                                    break
                                dst.write(data)
                        extracted_count += 1
    except Exception as e:
        return (zip_path, str(e), 0)
    return (None, None, extracted_count)


def process_all_contracts_optimized(root_dir, output_dir, num_processes):
    """优化后的全合约提取（使用ProcessPoolExecutor）"""
    start_time = time.time()

    # 构建交易所映射表（提前统一转为大写）
    exchange_map = {}
    for exchange, contracts in EXCHANGE_CONTRACTS.items():
        for contract in contracts:
            exchange_map[contract.upper()] = exchange

    # 任务生成器（延迟加载）
    def task_generator():
        for year in range(2011, 2026):
            year_dir = os.path.join(root_dir, str(year))
            if not os.path.exists(year_dir):
                continue
            for zip_file in os.listdir(year_dir):
                if zip_file.endswith('.zip'):
                    date_str = os.path.splitext(zip_file)[0]
                    yield (os.path.join(year_dir, zip_file), date_str)

    # 创建进程池
    mp_context = multiprocessing.get_context('spawn')
    with ProcessPoolExecutor(max_workers=num_processes, mp_context=mp_context) as executor:
        # 分批提交任务（减少调度开销）
        BATCH_SIZE = 200
        task_iter = task_generator()
        futures = []

        while True:
            batch = list(islice(task_iter, BATCH_SIZE))
            if not batch:
                break
            futures.extend(
                executor.submit(
                    process_single_zip_optimized,
                    task,
                    output_dir,
                    exchange_map
                ) for task in batch
            )

        # 进度条配置
        total_tasks = len(futures)
        progress = tqdm(
            as_completed(futures),
            total=total_tasks,
            bar_format=f"{Fore.BLUE}{{l_bar}}{{bar:50}}{Style.RESET_ALL} {{n_fmt}}/{{total_fmt}}",
            desc=f"{Fore.BLUE}提取进度",
            dynamic_ncols=True
        )

        # 结果处理
        total_extracted = 0
        errors = []
        for future in progress:
            result = future.result()
            if result[0]:
                errors.append(f"{os.path.basename(result[0])}: {result[1]}")
            total_extracted += result[2]

            # 动态更新描述信息
            progress.set_description(
                f"{Fore.BLUE}提取进度 [已提取 {Fore.GREEN}{total_extracted}{Fore.BLUE} 文件]"
            )

    # 统计信息输出
    time_cost = time.time() - start_time
    print(f"\n{Fore.GREEN}✅ 任务完成！共提取 {Fore.YELLOW}{total_extracted} {Fore.GREEN}个文件")
    print(f"{Fore.GREEN}🕒 耗时：{Fore.YELLOW}{time_cost:.2f}秒")
    print(f"{Fore.GREEN}📁 保存路径：{Fore.CYAN}{os.path.abspath(output_dir)}")

    if errors:
        print(f"\n{Fore.RED}⚠ 遇到 {len(errors)} 个错误：")
        for error in errors[:3]:
            print(f"• {error}")
        if len(errors) > 3:
            print(f"{Fore.YELLOW}（仅显示前3个错误，共{len(errors)}个）")


def extract_specific_contract(contract_name, root_dir, output_dir):
    """模式1：导出指定合约"""
    pattern = re.compile(rf"^{re.escape(contract_name)}\.csv$", re.IGNORECASE)
    process_zips(root_dir, output_dir, pattern)


def extract_product_contracts(product_code, root_dir, output_dir):
    """模式2：导出指定品种的所有合约"""
    pattern = re.compile(
        rf"^{re.escape(product_code)}\d{{3,4}}\.csv$",
        re.IGNORECASE
    )
    process_zips(root_dir, output_dir, pattern)


def process_zips(root_dir, output_dir, pattern):
    """通用处理函数（单线程）"""
    total_files = 0
    start_time = time.time()

    for year in range(2011, 2026):
        year_dir = os.path.join(root_dir, str(year))
        if not os.path.exists(year_dir):
            print(f"{Fore.YELLOW}⚠ 跳过不存在的年份目录：{year}")
            continue

        zip_files = sorted([f for f in os.listdir(year_dir) if f.endswith(".zip")])
        print(f"\n{Fore.MAGENTA}📅 正在处理 {year} 年数据（共 {len(zip_files)} 个交易日）")

        for zip_file in zip_files:
            zip_path = os.path.join(year_dir, zip_file)
            date_str = os.path.splitext(zip_file)[0]

            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    date_dir = os.path.join(output_dir, date_str)
                    os.makedirs(date_dir, exist_ok=True)

                    matched = [f for f in zf.namelist() if pattern.match(f)]
                    if matched:
                        print(f"\n{Fore.GREEN}🔍 在 {zip_file} 中发现 {len(matched)} 个匹配：")

                    for csv_file in matched:
                        dest_path = os.path.join(date_dir, csv_file)
                        if not os.path.exists(dest_path):
                            zf.extract(csv_file, date_dir)
                            total_files += 1
                            print(f"   {Fore.WHITE}→ {Fore.CYAN}{csv_file}")
                        else:
                            print(f"{Fore.YELLOW}⏩ 跳过已存在文件：{csv_file}")
            except Exception as e:
                print(f"\n{Fore.RED}⚠ 处理 {zip_file} 时出错：{str(e)}")

    time_cost = time.time() - start_time
    print(f"\n{Fore.GREEN}✅ 任务完成！共提取 {Fore.YELLOW}{total_files} {Fore.GREEN}个文件")
    print(f"{Fore.GREEN}🕒 耗时：{Fore.YELLOW}{time_cost:.2f}秒")


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()

    # 操作说明
    print(f"{Fore.WHITE}📌 格式要求：")
    print(f"1. 源档案目录结构：{Fore.CYAN}根目录/2014/合约文件.zip")
    print(f"2. 自动跳过已存在的文件{Fore.YELLOW}（避免重复提取）\n")

    # 模式选择
    print(f"{Fore.MAGENTA}🌸 请选择操作模式：")
    print(f"{Fore.WHITE}1. {Fore.CYAN}精确合约提取（如 M2309）")
    print(f"{Fore.WHITE}2. {Fore.CYAN}全品种合约提取（如 MA）")
    print(f"{Fore.WHITE}3. {Fore.CYAN}全市场一键提取（多进程加速）\n")

    while True:
        mode = input(f"{Fore.YELLOW}➤ 请输入模式编号 (1/2/3): ").strip()
        if mode in ("1", "2", "3"):
            break
        print(f"{Fore.RED}❌ 输入错误，请重新输入")

    # 路径处理
    print(f"\n{Fore.MAGENTA}📂 路径设置：")
    root_dir = input(f"{Fore.YELLOW}➤ 请输入原始数据根目录: ").strip()
    output_dir = input(f"{Fore.YELLOW}➤ 请输入输出目录（默认：./output）: ").strip() or "output"
    os.makedirs(output_dir, exist_ok=True)

    # 模式分支
    if mode == "1":
        print(f"\n{Fore.MAGENTA}🎯 精确合约提取模式：")
        while True:
            contract = input(f"{Fore.YELLOW}➤ 请输入交割合约代码（如 FG2405 或 m111）: ").strip().upper()
            if re.match(r"^[A-Z]{1,4}\d{3,4}$", contract):
                break
            print(f"{Fore.RED}❌ 格式错误！示例：{Fore.CYAN}M111（3位）{Fore.RED}或 {Fore.CYAN}MA2405（4位）")
        extract_specific_contract(contract, root_dir, output_dir)

    elif mode == "2":
        print(f"\n{Fore.MAGENTA}🌐 全品种提取模式：")
        while True:
            product = input(f"{Fore.YELLOW}➤ 请输入合约品种代码（如 FG、MA）: ").strip().upper()
            if re.match(r"^[A-Z]{1,4}$", product):
                break
            print(f"{Fore.RED}❌ 格式错误！示例：{Fore.CYAN}M {Fore.RED}或 {Fore.CYAN}AG")
        extract_product_contracts(product, root_dir, output_dir)

    elif mode == "3":
        print(f"\n{Fore.MAGENTA}🚀 全市场一键提取模式：")
        default_procs = multiprocessing.cpu_count()
        while True:
            procs_input = input(f"{Fore.YELLOW}➤ 请输入使用的进程数（默认{default_procs}）: ").strip()
            if not procs_input:
                num_procs = default_procs
                break
            if procs_input.isdigit() and int(procs_input) > 0:
                num_procs = int(procs_input)
                break
            print(f"{Fore.RED}❌ 输入错误，请输入正整数")
        process_all_contracts_optimized(root_dir, output_dir, num_procs)

    # 结束提示
    print(f"{Fore.GREEN}\n✨ 提示：每个交易日的合约文件存储在对应的交易所/日期目录中")