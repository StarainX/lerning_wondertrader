# -*- coding: utf-8 -*-
import os
import re
import zipfile
import time
from tqdm import tqdm
from colorama import Fore, Style, init

# 初始化颜色支持（Windows需要）
init(autoreset=True)


def print_banner():
    """打印艺术字横幅"""
    title = "★☆★ 楠哥哥的tick提取工具箱 ★☆★"
    author = "作者：Deepseek、吉哈德韦伯"
    print(Fore.CYAN + "\n" + "=" * 90)
    print(Fore.CYAN + f"{title:^90}")
    print(Fore.CYAN + "=" * 90)
    print(f"{author:>88}")
    print()


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
    """通用处理函数（按日期分目录存储）"""
    total_files = 0
    start_time = time.time()

    # 进度条样式配置
    bar_format = f"{Fore.BLUE}{{l_bar}}{{bar:50}}{Style.RESET_ALL} {{n_fmt}}/{{total_fmt}}"

    for year in range(2011, 2026):
        year_dir = os.path.join(root_dir, str(year))
        if not os.path.exists(year_dir):
            print(f"{Fore.YELLOW}⚠ 跳过不存在的年份目录：{year}")
            continue

        zip_files = sorted([f for f in os.listdir(year_dir) if f.endswith(".zip")])
        print(f"\n{Fore.MAGENTA}📅 正在处理 {year} 年数据（共 {len(zip_files)} 个交易日）")

        for zip_file in tqdm(zip_files, desc=f"{Fore.BLUE}扫描进度", bar_format=bar_format):
            zip_path = os.path.join(year_dir, zip_file)
            date_str = os.path.splitext(zip_file)[0]  # 获取日期字符串

            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    # 创建日期子目录
                    date_dir = os.path.join(output_dir, date_str)
                    os.makedirs(date_dir, exist_ok=True)

                    matched = [f for f in zf.namelist() if pattern.match(f)]

                    if matched:
                        print(f"\n{Fore.GREEN}🔍 在 {zip_file} 中发现 {len(matched)} 个匹配：")

                    for csv_file in matched:
                        # 生成新文件名（保留原始合约文件名）
                        new_name = os.path.basename(csv_file)
                        dest_path = os.path.join(date_dir, new_name)

                        # 检查文件是否已存在
                        if not os.path.exists(dest_path):
                            zf.extract(csv_file, date_dir)
                            print(f"   {Fore.WHITE}→ {Fore.CYAN}{new_name}")
                            total_files += 1
                        else:
                            print(f"{Fore.YELLOW}⏩ 跳过已存在文件：{new_name}")

            except Exception as e:
                print(f"\n{Fore.RED}⚠ 处理 {zip_file} 时出错：{str(e)}")

    time_cost = time.time() - start_time
    print(f"\n{Fore.GREEN}✅ 任务完成！共提取 {Fore.YELLOW}{total_files} {Fore.GREEN}个文件")
    print(f"{Fore.GREEN}🕒 耗时：{Fore.YELLOW}{time_cost:.2f}秒")
    print(f"{Fore.GREEN}📁 保存路径：{Fore.CYAN}{os.path.abspath(output_dir)}")
    print("\n" + "★" * 90 + "\n")


def validate_product_code(input_str):
    """验证品种代码格式"""
    return bool(re.match(r"^[a-zA-Z]{1,4}$", input_str))


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')  # 清屏
    print_banner()

    # 操作说明
    print(f"{Fore.WHITE}📌 格式要求：")
    print(f"1. 源档案目录结构：{Fore.CYAN}根目录/2014/合约文件.zip")
    print(f"2. 自动跳过已存在的文件{Fore.YELLOW}（避免重复提取）\n")

    # 模式选择
    print(f"{Fore.MAGENTA}🌸 请选择操作模式：")
    print(f"{Fore.WHITE}1. {Fore.CYAN}精确合约提取（如 M2309）")
    print(f"{Fore.WHITE}2. {Fore.CYAN}全品种合约提取（如 MA）\n")

    while True:
        mode = input(f"{Fore.YELLOW}➤ 请输入模式编号 (1/2): ").strip()
        if mode in ("1", "2"):
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
            if validate_product_code(product):
                break
            print(f"{Fore.RED}❌ 格式错误！示例：{Fore.CYAN}M {Fore.RED}或 {Fore.CYAN}AG")
        extract_product_contracts(product, root_dir, output_dir)

    # 结束提示
    print(f"{Fore.GREEN}\n✨ 提示：每个交易日的合约文件存储在对应的日期目录中")