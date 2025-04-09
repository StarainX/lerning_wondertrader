#### WtBtAnalyst是绩效分析模块，里面主要是一堆绩效相关数据的计算，值得注意的是下面四个调用方法。

* run()：遍历策略生成资金分析的xlsx文件

* run_simple():遍历策略生成资金分析summary.json

* run_new():遍历策略生成交易和资金分析的xlsx文件和summary.json

* run_flat():遍历策略进行逐笔分析和汇总并生成rdana.json、rndana.json和summary.json

这里面有个小坑是 其中run_new()和run_flat()不支持HFT引擎，从debug来看貌似是数据处理过程中缺少某个字段的缘故。
貌似也不支持testsnopper。暂不清楚是否能够自己修改wtpy部分的代码解决这一问题。
