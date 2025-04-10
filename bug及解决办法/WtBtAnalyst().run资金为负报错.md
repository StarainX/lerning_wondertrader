该方法是比较简易的绩效分析方法，好处是兼容cta、hft。

调用该方法运行可能抛出下面一个错误：
```
…………前方省略…………
ar = math.pow(ayNetVals.iloc[-1], annual_days/days) - 1 #年化收益率=总收益率^(年交易日天数/统计天数) ValueError: math domain error
```

这个问题是因为资金为负无效计算绩效……而WtBtAnalyst().run方法中没有加入资金为空或负值的判断。

解决方法替换funds_analyze方法中下面这句：

```
ar = math.pow(ayNetVals.iloc[-1], annual_days/days) - 1
……
```


参照summary_analyze中的写法替换成下面的判断逻辑：
```
    if ayNetVals.iloc[-1] >= 0:
        ar = math.pow(ayNetVals.iloc[-1], annual_days / days) - 1  # 年化收益率=总收益率^(年交易日天数/统计天数)
    else:
        ar = -9999

```

然应该是为了回测速度考虑所以没有加入判断逻辑。
