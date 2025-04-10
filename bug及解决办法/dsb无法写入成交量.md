
bug已经上报[issue](https://github.com/wondertrader/wtpy/issues/159)。

这个问题测试了下，在0.9以后直到最新的dev版本都存在，再往前没有试。

问题复现直接运行dev版的test_datahelper下的testDtHelper.py即可。
本来其中的以下语句会打印出WTSBarStruct的第一行和最后一行数据。

```
    print(buffer[0].to_dict())
    print(buffer[-1].to_dict())
```
不过这个问题之所以没有被发现，很大程度上是因为这两个语句虽然在def test_store_bars()方法中，但该方法本身并没有在该例子中被调用过。

在该方法下方任意位置加入调用：
`test_store_bars()`

可以看出输出结果如下：
```
{'date': 20140102, 'reserve': 0, 'time': 2401020935, 'open': 2342.2, 'high': 2343.4, 'low': 2339.2, 'close': 2343.2, 'settle': 0.0, 'turnover': 0.0, 'volume': 0.0, 'open_interest': 0.0, 'diff': 0.0}
{'date': 20191031, 'reserve': 0, 'time': 2910311500, 'open': 3872.4, 'high': 3879.0, 'low': 3872.4, 'close': 3879.0, 'settle': 0.0, 'turnover': 0.0, 'volume': 0.0, 'open_interest': 0.0, 'diff': 0.0}

```

成交量显示为0.

debug过程中发现WtCoreDefs.py中定义的数据结构中不是vol而是volume：
`class WTSBarStruct(WTSStruct):
    '''
    C接口传递的bar数据结构
    '''
    # @2IQ9d
    _fields_ = [("date", c_uint32),
                ("reserve", c_uint32),
                ("time", c_uint64),
                ("open", c_double),
                ("high", c_double),
                ("low", c_double),
                ("close", c_double),
                ("settle", c_double),
                ("turnover", c_double),
                ("volume", c_double),
                ("open_interest", c_double),
                ("diff", c_double)]
    _pack_ = 8
`

有个解决办法是将上面WTSBarStruct的volume修改为vol（实际上写入dsb依旧是写入到volume字段）。因为写入过程中检查的是vol字段而不是volume，如果直接调用之前重命名的vol改为volume会出现找不到vol的报错。


比如把testDtHelper.py中下方的‘vol’修改为volume，就会报错找不到vol index：
```
def test_store_bars():
    df = pd.read_csv('../storage/csv/CFFEX.IF.HOT_m5.csv')
    df = df.rename(columns={
        '<Date>':'date',
        ' <Time>':'time',
        ' <Open>':'open',
        ' <High>':'high',
        ' <Low>':'low',
        ' <Close>':'close',
        ' <Volume>':'vol',
        })

```
报错如下：
```

    indexer = self.columns._get_indexer_strict(key, "columns")[1]
  File "C:\ProgramData\anaconda3\envs\python38\lib\site-packages\pandas\core\indexes\base.py", line 5877, in _get_indexer_strict
    self._raise_if_missing(keyarr, indexer, axis_name)
  File "C:\ProgramData\anaconda3\envs\python38\lib\site-packages\pandas\core\indexes\base.py", line 5941, in _raise_if_missing
    raise KeyError(f"{not_found} not in index")
KeyError: "['vol'] not in index"

```
本来想把报错里的用来index的vol直接改成volume以统一，但是这个逻辑似乎没有在python层没找到，猜是包装在C++层了？