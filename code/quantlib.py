import pandas as pd
import logging
class QuantBox:
    @staticmethod
    def dayAndnight(df: pd.DataFrame, time_column: str = 'UpdateTime') -> pd.DataFrame:
        """
        清理并处理市场数据，优先处理夜盘（存在20:59:00时），若无夜盘，处理早盘（存在08:59:00时）。
        参数：
            df: 原始数据集（需按时间排序）
            time_column: 时间戳列的名称，默认为 'UpdateTime'
        返回：
            清洗后的DataFrame
        """
        if df.empty:
            logging.warning("输入数据为空，返回原始数据")
            return df

        if time_column not in df.columns:
            raise KeyError(f"DataFrame 缺少 '{time_column}' 列")

        NIGHT_TARGET_TIME = '20:59:00'
        MORNING_TARGET_TIME = '08:59:00'

        target_time = None

        if NIGHT_TARGET_TIME in df[time_column].values:
            logging.info("检测到夜盘数据，开始清洗...")
            target_time = NIGHT_TARGET_TIME
        elif MORNING_TARGET_TIME in df[time_column].values:
            logging.info("检测到早盘数据，开始清洗...")
            target_time = MORNING_TARGET_TIME
        else:
            logging.info("无夜盘/早盘标记，保留原始数据")
            return df

        if target_time is None:
            logging.warning("未提供目标时间戳，返回原始数据")
            return df

        # 查找目标时间戳的索引
        condition = df[time_column] == target_time
        indices = df.index[condition]

        if not indices.empty:
            last_idx = indices.max()
            df = df.loc[last_idx:].copy()  # 截断数据，避免链式赋值警告

            # 确保截断后的数据中只有一条目标记录
            new_condition = df[time_column] == target_time
            new_indices = df.index[new_condition]
            if len(new_indices) > 1:
                final_idx = new_indices.max()
                df = df.loc[final_idx:]

        return df
    @staticmethod
    def plus_ms(df,UpdateTime='UpdateTime',UpdateMillisec='UpdateMillisec'):
        """
        UpdateTime是判断时间戳相同的列，UpdateMillisec是+ms的列。
        该函数作用是让时间戳不相同，兼容500ms和250ms推送
        """
        # 列存在性验证
        required_cols = [UpdateTime, UpdateMillisec]
        if not set(required_cols).issubset(df.columns):
            missing = set(required_cols) - set(df.columns)
            raise ValueError(f"缺失必要列: {missing}")

        original_columns = df.columns.tolist()  # 新增：保存原始列顺序
        df = df.reset_index(drop=True)
        # 生成连续时间戳分组标识
        df['_group'] = (df[UpdateTime] != df[UpdateTime].shift()).cumsum()

        # 预计算分组特征
        group_info = df.groupby('_group').size().reset_index(name='_size')
        df = df.merge(group_info, on='_group')
        df['_pos'] = df.groupby('_group').cumcount()

        # 标记需删除的超量行
        df['_del'] = (df['_size'] > 4) & (df['_pos'] >= 4)

        # 毫秒增量规则配置
        increment_rules = [
            (df['_size'] == 2) & (df['_pos'] == 1),
            (df['_size'] >= 3) & (df['_pos'] == 1),
            (df['_size'] >= 3) & (df['_pos'] == 2),
            (df['_size'] >= 4) & (df['_pos'] == 3)
        ]
        increments = [500, 250, 500, 750]

        # 应用增量到指定列
        for condition, inc in zip(increment_rules, increments):
            df.loc[condition, UpdateMillisec] += inc

        # 生成最终结果
        result_df = df[~df['_del']].drop(
            ['_group', '_size', '_pos', '_del'], axis=1)
        return result_df[original_columns]  # 使用保存的原始列顺序